import piecash
from json import load as jsonload
from pathlib import Path
import pandas as pd
from datetime import datetime
from decimal import Decimal

# TODO
# # Add Log file functionality
# # Add date distance tolerance to the internal transactions determination
# # # # ie. do not combine two transactions unless they are within two days of each other


def do_csv2cash(path_to_Book, path_to_rawdata, path_to_translationJSON):
    translation = get_translation(path_to_translationJSON)
    rawdata = get_rawdata(path_to_rawdata)
    rawdata_prepped = translateandprep_rawdata(translation, rawdata)
    transactions_compiled = compile_transfers(rawdata_prepped)
    import2cash(transactions_compiled, path_to_Book)


def get_compiled_transactions(path_to_rawdata,
                              path_to_translationJSON,
                              returnall=False):
    translation = get_translation(path_to_translationJSON)
    rawdata = get_rawdata(path_to_rawdata)
    rawdata_prepped = translateandprep_rawdata(translation, rawdata)
    transactions_compiled = compile_transfers(rawdata_prepped)

    if not returnall: return (transactions_compiled)
    if returnall:
        return (transactions_compiled, translation, rawdata, rawdata_prepped)


def get_uncat_transfers(path_to_rawdata, path_to_translationJSON):

    rawdata = get_rawdata(path_to_rawdata)
    translation = get_translation(path_to_translationJSON)

    rawdata = translateandprep_rawdata(translation, rawdata)

    return (rawdata.loc[(rawdata['category_mod'] == 'Uncategorized')])


def write_account_list(path_to_Book, path_to_accountlistfile):
    """ Write list of accounts in book to a text file"""
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
    with path_to_translationJSON.open() as translationjson:
        return (jsonload(translationjson))


def get_rawdata(path_to_rawdata):
    return (pd.read_csv(path_to_rawdata))


##########################################################################
#----rawdata TRANSLATING & PREP------
##########################################################################
def translateandprep_rawdata(translation, rawdata):
    return (translating_rawdata(translation, preping_rawdata(rawdata)))


def translating_rawdata(translation, rawdata):

    amount_mod = []
    account_mod = []
    category_mod = []
    for _, row in rawdata.iterrows():
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
    # See if any duplicates exist. This is to track transfers between equity accounts (ie. internal transactions)
    rawdata['duplicatetf'] = rawdata.duplicated(subset='Amount', keep=False)

    # Add a checkmark column to the data. If True, then the data has been transferred to the transactions_compiled DataFrame
    rawdata['is_claimed'] = False

    return (rawdata)


##########################################################################
#----------RAW DATA --> gnuCASH COMPATIBLE DATA---------------------------
##########################################################################


def compile_transfers(rawdata):
    transactions_compiled = pd.DataFrame(
        columns=['description', 'post_date', 'note', 'split1', 'split2'])

    for index, current_transaction in rawdata.iterrows():
        if rawdata.at[index, 'is_claimed'] == False:
            # Separating the external transactions from internal. Duplicate indicates internal transaction
            internalTrans_tf = _is_internalTransaction(current_transaction,
                                                       rawdata)
            if not internalTrans_tf:
                transactions_compiled = _externalTransactions_append(
                    current_transaction, rawdata, transactions_compiled, index)

            # Work on Internal transactions
            elif internalTrans_tf:
                nearest_duplicate = _determine_internalTransactions(
                    current_transaction, rawdata)

                transactions_compiled = _internalTransaction_append(
                    current_transaction, nearest_duplicate, rawdata,
                    transactions_compiled, index)

    return (transactions_compiled)


def _externalTransactions_append(current_transaction, rawdata,
                                 transactions_compiled, index):
    """
    Function to append the external transaction data to the compiled DataFrame
    
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
    rawdata.at[index, 'is_claimed'] = True
    return (transactions_compiled)


def _internalTransaction_append(current_transaction, nearest_duplicate, rawdata,
                                transactions_compiled, index):
    """
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

    split1, split2, temp = {}, {}, {}

    temp[
        'description'] = current_transaction['Description'] + ' ' + nearest_duplicate['Description']
    temp['post_date'] = max(current_transaction['Date'],
                            nearest_duplicate['Date'])
    temp['note'] = str(current_transaction['Notes']
                      ) + current_transaction['Original Description']
    split1['account'] = current_transaction['account_mod']
    split1['value'] = current_transaction['amount_mod']
    split2['account'] = nearest_duplicate['account_mod']
    split2['value'] = nearest_duplicate['amount_mod']

    temp['split1'] = pd.Series(split1)
    temp['split2'] = pd.Series(split2)

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)

    # Mark the transactions has claimed; prevents duplicate in transaction_compiled
    rawdata.at[index, 'is_claimed'] = True
    rawdata.at[nearest_duplicate['rawdataindex'], 'is_claimed'] = True

    # Change category_mod to Internal transaction. Helps distinguish transactions from one another.
    rawdata.at[index, 'category_mod'] = 'Internal Transaction'
    rawdata.at[nearest_duplicate['rawdataindex'],
               'category_mod'] = 'Internal Transaction'
    return (transactions_compiled)


def _determine_internalTransactions(current_transaction, rawdata):
    """ Determines the corresponding transaction to current_transaction"""

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
    return (nearest_duplicate)


def _is_internalTransaction(current_transaction, rawdata):
    """ Determines whether the current_transaction is internal"""
    if not current_transaction['duplicatetf']:
        return (False)

    elif current_transaction['duplicatetf']:
        # Find all transactions that have the inverse amount and haven't been transferred
        identical_duplicates = rawdata.loc[
            (rawdata['amount_mod'] == -current_transaction['amount_mod']) &
            (rawdata['is_claimed'] != True)]
        if len(identical_duplicates) != 0:
            return (True)


##########################################################################
#-----------PUTTING DATA IN GNUCASH--------------------------------------
##########################################################################
def import2cash(transactions_compiled, path_to_Book):
    """Import compiled transactions into the GNUCash Book"""

    book = piecash.open_book(path_to_Book.as_posix(), readonly=False)

    # if the GNUCash Book has one currency, use that currency
    if len(book.commodities) == 1:
        currency = book.commodities[0]
    else:
        raise RuntimeError('GNUCash Book must have 1 commodity. Please make GitHub issue if this is an issue for you.')

    # create "Uncategorized" account if none exists
    try:
        book.accounts(name='Uncategorized')
    except:
        _ = piecash.Account(
            "Uncategorized", "EXPENSE", currency, parent=book.root_account)
        book.save()

    for _, transaction in transactions_compiled.iterrows():
        _ = piecash.Transaction(
            currency=currency,
            description=transaction['description'],
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
