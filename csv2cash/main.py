import piecash
from json import load as jsonload
from pathlib import Path
import pandas as pd
from datetime import datetime
from decimal import Decimal
import logging

# TODO
# # Add Log file functionality

logging.basicConfig(
    format=
    '%(asctime)s, %(levelname)-8s [%(filename)s:%(module)s:%(funcName)s:%(lineno)d] %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def do_csv2cash(path_to_Book, path_to_rawdata, path_to_translationJSON):
    """Performs all csv -> GNUCash operations"""

    logger.info(f'Function start arguments: {locals()}')

    translation = get_translation(path_to_translationJSON)
    rawdata = get_rawdata(path_to_rawdata)
    logger.info(f'Number of rows in rawdata: {len(rawdata.index)}')

    rawdata_prepped = translateandprep_rawdata(translation, rawdata)
    transactions_compiled = compile_transfers(rawdata_prepped)
    import2cash(transactions_compiled, path_to_Book)


def get_compiled_transactions(path_to_rawdata,
                              path_to_translationJSON,
                              returnall=False):
    """Returns DataFrame of compiled transactions"""

    logger.info(f'Function start arguments: {locals()}')

    translation = get_translation(path_to_translationJSON)
    rawdata = get_rawdata(path_to_rawdata)
    rawdata_prepped = translateandprep_rawdata(translation, rawdata)
    transactions_compiled = compile_transfers(rawdata_prepped)

    if not returnall:
        return (transactions_compiled)
    else:
        return (transactions_compiled, translation, rawdata, rawdata_prepped)


def get_uncat_transfers(path_to_rawdata, path_to_translationJSON):
    """Returns DataFrame of uncategorized transfers"""

    logger.info(f'Function start arguments: {locals()}')

    rawdata = get_rawdata(path_to_rawdata)
    translation = get_translation(path_to_translationJSON)

    rawdata = translateandprep_rawdata(translation, rawdata)

    return (rawdata.loc[(rawdata['category_mod'] == 'Uncategorized')])


def write_account_list(path_to_Book, path_to_accountlistfile):
    """ Write list of accounts in book to a text file"""

    logger.info(f'Function start arguments: {locals()}')

    book = piecash.open_book(path_to_Book.as_posix())

    accountstr = ""
    for account in book.accounts:
        accountstr += account.fullname
        accountstr += '\n'

    path_to_accountlistfile.write_text(accountstr)


##########################################################################
#----GETTING DATA------
##########################################################################


# Open and make translations dictionary
def get_translation(path_to_translationJSON):
    """Returns dictionary with translations.json data"""

    logger.debug(f'Function start arguments: {locals()}')
    with Path(path_to_translationJSON).open() as translationjson:
        return (jsonload(translationjson))


def get_rawdata(path_to_rawdata):
    """Returns pandas DF of rawdata csv"""

    logger.debug(f'Function start arguments: {locals()}')
    return (pd.read_csv(path_to_rawdata))


##########################################################################
#----rawdata TRANSLATING & PREP------
##########################################################################
def translateandprep_rawdata(translation, rawdata):
    """Single function to combine translating_rawdata and preping_rawdata"""

    logger.info(f'Function start')
    return (translating_rawdata(translation, preping_rawdata(rawdata)))


def translating_rawdata(translation, rawdata):
    """Translates the rawdata using translation.json dictionary

    Translates the amount, account, and label of the rawdata based on the dictionary provided by 'translations.json' file. Also filters out transfers that match an 'IGNORE' translation.
    
    Parameters
    ----------
    translation : dict of dicts
        Holds the tranlastions from rawdata values to GNUCash values. Created using 'translations.json' file.
    rawdata : DataFrame
        The csv data after going through preping_rawdata().
    
    Returns
    -------
    DataFrame
        csv data with it's contents translated and filtered out.
    """

    logger.info(f'Function start')

    amount_mod = []
    account_mod = []
    category_mod = []
    for index, row in rawdata.iterrows():
        logger.debug(f'RAWINDEX={index}, translation started')

        # Make list of transaction values with negatives
        if row['Transaction Type'] == 'debit':
            amount_mod.append(Decimal(str(-row['Amount'])))
        else:
            amount_mod.append(Decimal(str(row['Amount'])))

        # Make list of translated Accounts
        if row['Account Name'] in translation['Accounts'].keys():
            account_mod.append(translation['Accounts'][row['Account Name']])
        else:
            account_mod.append(translation['Accounts']['Uncategorized'])

        # Make list of translated Categories
        if row['Category'] in translation['Categories'].keys():
            category_mod.append(translation['Categories'][row['Category']])
        else:
            category_mod.append(translation['Categories']['Uncategorized'])

        logger.debug(
            f'RAWINDEX={index}, translated values: amount_mod={amount_mod[-1]}, account_mod={account_mod[-1]}, category_mod={category_mod[-1]}'
        )

    rawdata['amount_mod'] = amount_mod
    rawdata['account_mod'] = account_mod
    rawdata['category_mod'] = category_mod

    # If something is translated to 'IGNORE', then it will be dropped from rawdata
    rawdata = rawdata[(rawdata['category_mod'] !=
                       'IGNORE')][(rawdata['account_mod'] != 'IGNORE')]

    # Convert Date column to datetime object
    rawdata['Date'] = rawdata['Date'].apply(
        lambda x: datetime.strptime(x, '%m/%d/%Y'))

    return (rawdata)


def preping_rawdata(rawdata):
    """Finds duplicate transactions and adds 'is_claimed' column"""

    logger.info(f'Function start')

    # See if any duplicates exist. This is to track transfers between equity accounts (ie. internal transactions)
    rawdata['duplicatetf'] = rawdata.duplicated(subset='Amount', keep=False)

    # Add a checkmark column to the data. If True, then the data has been transferred to the transactions_compiled DataFrame
    rawdata['is_claimed'] = False

    return (rawdata)


##########################################################################
#----------RAW DATA --> gnuCASH COMPATIBLE DATA---------------------------
##########################################################################


def compile_transfers(rawdata):
    """Returns DataFrame of processed transaction data"""

    logger.info(f'Function start')

    transactions_compiled = pd.DataFrame(
        columns=['description', 'post_date', 'note', 'split1', 'split2'])

    for index, current_transaction in rawdata.iterrows():
        logger.debug(f'RAWINDEX={index}, Compilation process start')
        if rawdata.at[index, 'is_claimed'] == False:
            # Separating the external transactions from internal. Duplicate indicates internal transaction
            internalTrans_tf = _is_internalTransaction(current_transaction,
                                                       rawdata, index)
            if not internalTrans_tf:
                transactions_compiled = _externalTransactions_append(
                    current_transaction, rawdata, transactions_compiled, index)

            # Work on Internal transactions
            elif internalTrans_tf:
                nearest_duplicate = _determine_internalTransactions(
                    current_transaction, rawdata, index)

                transactions_compiled = _internalTransaction_append(
                    current_transaction, nearest_duplicate, rawdata,
                    transactions_compiled, index)

    return (transactions_compiled)


def _externalTransactions_append(current_transaction, rawdata,
                                 transactions_compiled, index):
    """Append the external transaction data to the compiled DataFrame
    
    Parameters
    ----------
    current_transaction : DataFrame
        The row that holds the transaction to be compiled
    rawdata : DataFrame
        The df that holds the initial data collected (rawdata)
    transactions_compiled : DataFrame
        The df that holds the compiled transaction data

    Returns
    -------
    DataFrame
        The transactions_compiled df with the data from current_transaction appended to it
    """

    logger.debug(f'RAWINDEX={index}, External Transaction being appended')

    split1, split2, temp = {}, {}, {}

    temp['description'] = current_transaction['Description']
    temp['post_date'] = current_transaction['Date']
    # The GNUCash note will be the 'Notes' and 'Original Description' concatenated
    temp['note'] = str(current_transaction['Notes']
                      ) + current_transaction['Original Description']
    split1['account'] = current_transaction['account_mod']
    split1['value'] = current_transaction['amount_mod']
    split2['account'] = current_transaction['category_mod']
    split2['value'] = -current_transaction['amount_mod']

    temp['split1'] = pd.Series(split1)
    temp['split2'] = pd.Series(split2)

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)
    logger.debug(f'RAWINDEX={index}, Transaction added successfully')

    rawdata.at[index, 'is_claimed'] = True
    return (transactions_compiled)


def _internalTransaction_append(current_transaction, nearest_duplicate, rawdata,
                                transactions_compiled, index):
    """Appends internal transaction to transactions_compiled

    Combines the current_transaction and nearest_duplicate into a single internal transaction statement and appends it to transactions_compiled
    
    Parameters
    ----------
    current_transaction : DataFrame
        The row from rawdata that holds one transaction statement to be compiled into a single other statement
    nearest_duplicate : DataFrame
        Same as current_transaction, but a different row.
    rawdata : DataFrame
        The df that holds the original data from the rawdata
    transactions_compiled : DataFrame
        The df that holds the compiled and processed transaction data

    Returns
    -------
    DataFrame
        The transactions_compiles df with the processed data from current_transaction and nearest_duplicate appended to it.
    """

    logger.debug(f'RAWINDEX={index}, Internal Transaction being appended')

    split1, split2, temp = {}, {}, {}

    # Add transaction information to temporary transaction series
    temp[
        'description'] = current_transaction['Description'] + ' ' + nearest_duplicate['Description']
    temp['post_date'] = max(current_transaction['Date'],
                            nearest_duplicate['Date'])
    temp['note'] = str(current_transaction['Notes']
                      ) + current_transaction['Original Description']

    # Organizes transfer info between split1 and split1
    split1['account'] = current_transaction['account_mod']
    split1['value'] = current_transaction['amount_mod']
    split2['account'] = nearest_duplicate['account_mod']
    split2['value'] = nearest_duplicate['amount_mod']

    # Add split1 and split2 info to temporary transaction Series
    temp['split1'] = pd.Series(split1)
    temp['split2'] = pd.Series(split2)

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)
    logger.debug(f'RAWINDEX={index}, Transaction added successfully')

    # Mark the transactions has claimed; prevents duplicate in transaction_compiled
    rawdata.at[index, 'is_claimed'] = True
    rawdata.at[nearest_duplicate['rawdataindex'], 'is_claimed'] = True

    # Change category_mod to Internal transaction. Helps distinguish transactions from one another.
    rawdata.at[index, 'category_mod'] = 'Internal Transaction'
    rawdata.at[nearest_duplicate['rawdataindex'],
               'category_mod'] = 'Internal Transaction'

    return (transactions_compiled)


def _determine_internalTransactions(current_transaction, rawdata, index):
    """Determines the corresponding transaction to current_transaction"""

    logger.debug(f'RAWINDEX={index}, determining corresponding transaction')

    # Find all transactions that have the inverse amount and haven't been transferred
    identical_duplicates = rawdata.loc[
        (rawdata['amount_mod'] == -current_transaction['amount_mod']) &
        (rawdata['is_claimed'] != True)]

    # Note that this assumes that there won't be an identical inverse transaction on the same day
    nearest_duplicate = min(
        identical_duplicates.iterrows(),
        key=lambda x: abs(x[1]['Date'] - current_transaction['Date']))

    # Add the index value of the rawdata. This is to mark it in the 'is_claimed' column of rawdata
    rawdataindex = nearest_duplicate[0]
    nearest_duplicate = nearest_duplicate[1]
    nearest_duplicate['rawdataindex'] = rawdataindex
    logger.debug(
        f'RAWINDEX={index}, Duplicate determined to be at RAWINDEX={rawdataindex}.'
    )

    return (nearest_duplicate)


def _is_internalTransaction(current_transaction, rawdata, index):
    """Determines whether the current_transaction is internal"""

    logger.debug(f'RAWINDEX={index}, determining transaction type')

    if not current_transaction['duplicatetf']:
        logger.debug(
            f'RAWINDEX={index}, Transfer has no duplicate, therefore external')
        return (False)

    elif current_transaction['duplicatetf']:
        # Find all transactions that have the inverse amount and haven't been transferred
        identical_duplicates = rawdata.loc[
            (rawdata['amount_mod'] == -current_transaction['amount_mod']) &
            (rawdata['is_claimed'] != True)]
        if len(identical_duplicates) != 0:
            logger.debug(
                f'RAWINDEX={index}, Transfer has duplicate and matching transfer, therefore internal'
            )
            return (True)
        else:
            logger.debug(
                f'RAWINDEX={index}, Transfer has duplicate but no matching transfer, therefore external'
            )
            logger.warning(
                f'RAWINDEX={index}, Transfer has duplicate but no matching transfer. Previous matches could\'ve been already claimed. Will assume the transaction is external. Be sure to check the transaction to be sure that it is parsed correctly.'
            )
            return (False)


##########################################################################
#-----------PUTTING DATA IN GNUCASH--------------------------------------
##########################################################################
def import2cash(transactions_compiled, path_to_Book):
    """Write compiled transactions to GNUCash Book"""

    logger.info(f'Function start')
    logger.info(f'Length of transactions_compiled: {len(transactions_compiled.index)}')

    book = piecash.open_book(path_to_Book.as_posix(), readonly=False)

    # if the GNUCash Book has one currency, use that currency
    if len(book.commodities) == 1:
        currency = book.commodities[0]
    else:
        raise RuntimeError(
            'GNUCash Book must have 1 commodity. Please make GitHub issue if this is an issue for you.'
        )

    # create "Uncategorized" account if none exists
    try:
        book.accounts(name='Uncategorized')
    except:
        _ = piecash.Account(
            "Uncategorized", "EXPENSE", currency, parent=book.root_account)
        book.save()

    for index, transaction in transactions_compiled.iterrows():
        logger.debug(
            f'COMPILEDINDEX={index}, writing transaction to GNUCashBook')
        _ = piecash.Transaction(
            currency=currency,
            description=transaction['description'],
            post_date=transaction['post_date'].date(),
            splits=[
                piecash.Split(
                    account=book.accounts(
                        name=transaction['split1']['account']),
                    value=transaction['split1']['value']),
                piecash.Split(
                    account=book.accounts(
                        name=transaction['split2']['account']),
                    value=transaction['split2']['value'])
            ])

    book.save()
