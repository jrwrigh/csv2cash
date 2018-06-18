import piecash
from json import load as jsonload
from pathlib import Path
import pandas as pd
from datetime import datetime
from IPython.core.debugger import set_trace
import dfgui  #<-- note this is only for DF visualization. Not required for CLI
from decimal import Decimal

# TODO
# # Add Log file functionality
# # Add date distance tolerance to the internal transactions determination
# # # # ie. do not combine two transactions unless they are within two days of each other

##########################################################################
#------------INPUTS----------
##########################################################################

write_to_book = True

path_to_CSV = Path.cwd() / 'transactions_testPUBLIC.csv'
# path_to_CSV = Path.cwd() / 'transactions_test.csv'
# path_to_CSV = Path.cwd() / 'transactions.csv'
path_to_Book = Path.cwd() / 'test.gnucash'
path_to_translationJSON = Path.cwd() / 'translations.json'

##########################################################################
#--------READ IN DATA--------
##########################################################################

# Open and make translations dictionary
with path_to_translationJSON.open() as translationjson:
    translation = jsonload(translationjson)

csv = pd.read_csv(path_to_CSV)

##########################################################################
#----CSV TRANSLATING & PREP------
##########################################################################

amount_mod = []
account_mod = []
category_mod = []
for index, row in csv.iterrows():
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

csv['amount_mod'] = amount_mod
csv['account_mod'] = account_mod
csv['category_mod'] = category_mod

# Convert Date column to datetime object
csv['Date'] = csv['Date'].apply(lambda x: datetime.strptime(x, '%m/%d/%Y'))

# See if any duplicates exist. This is to track transfers between equity accounts (ie. internal transactions)
csv['duplicatetf'] = csv.duplicated(subset='Amount', keep=False)

# Add a checkmark column to the data. If True, then the data has been transferred to the transactions_compiled DataFrame
csv['is_claimed'] = False

##########################################################################
#--------FUNCTIONS FOR RAW DATA INTERPRETATION----------------------------
##########################################################################


def externalTransactions_append(current_transaction, raw_data,
                                transactions_compiled):
    """
    Function to append the external transaction data to the compiled DataFrame
    
    Parameters
    ----------
    current_transaction : DataFrame
        The row that holds the transaction to be compiled
    raw_data : DataFrame
        The df that holds the initial data collected (csv)
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

    temp['split1'] = split1
    temp['split2'] = split2

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)
    raw_data.at[index, 'is_claimed'] = True
    return (transactions_compiled)


def internalTransaction_append(current_transaction, nearest_duplicate, raw_data,
                               transactions_compiled):
    """
    Combines the current_transaction and nearest_duplicate into a single internal transaction statement and appends it to transactions_compiled
    
    Parameters
    ----------
    current_transaction : DataFrame
        The row from raw_data that holds one transaction statement to be compiled into a single other statement
    nearest_duplicate : DataFrame
        Same as current_transaction, but a different row.
    raw_data : DataFrame
        The df that holds the original data from the csv
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

    temp['split1'] = split1
    temp['split2'] = split2

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)

    # Mark the transactions has claimed; prevents duplicate in transaction_compiled
    raw_data.at[index, 'is_claimed'] = True
    raw_data.at[nearest_duplicate['raw_dataindex'], 'is_claimed'] = True

    # Change category_mod to Internal transaction. Helps distinguish transactions from one another.
    raw_data.at[index, 'category_mod'] = 'Internal Transaction'
    raw_data.at[nearest_duplicate['raw_dataindex'],
                'category_mod'] = 'Internal Transaction'
    return (transactions_compiled)


def determine_internalTransactions(current_transaction, raw_data):
    """ Determines the corresponding transaction to current_transaction"""

    # Find all transactions that have the inverse amount and haven't been transferred
    identical_duplicates = raw_data.loc[
        (raw_data['amount_mod'] == -current_transaction['amount_mod']) &
        (raw_data['is_claimed'] != True)]

    # Note that this assumes that there won't be an identical inverse transaction on the same day
    nearest_duplicate = min(
        identical_duplicates.iterrows(),
        key=lambda x: abs(x[1]['Date'] - current_transaction['Date']))

    # Add the index value of the raw_data. This is to mark it in the 'is_claimed' column of raw_data
    raw_dataindex = nearest_duplicate[0]
    nearest_duplicate = nearest_duplicate[1]
    nearest_duplicate['raw_dataindex'] = raw_dataindex
    return (nearest_duplicate)


def is_internalTransaction(current_transaction, raw_data):
    """ Determines whether the current_transaction is internal"""
    if not current_transaction['duplicatetf']:
        return (False)

    elif current_transaction['duplicatetf']:
        # Find all transactions that have the inverse amount and haven't been transferred
        identical_duplicates = raw_data.loc[
            (raw_data['amount_mod'] == -current_transaction['amount_mod']) &
            (raw_data['is_claimed'] != True)]
        if len(identical_duplicates) != 0:
            return (True)


##########################################################################
#----------RAW DATA --> gnuCASH COMPATIBLE DATA---------------------------
##########################################################################

transactions_compiled = pd.DataFrame(
    columns=['description', 'post_date', 'note', 'split1', 'split2'])

for index, current_transaction in csv.iterrows():
    if csv.at[index, 'is_claimed'] == False:
        split1, split2, temp = {}, {}, {}
        # Separating the external transactions from internal. Duplicate indicates internal transaction
        internalTrans_tf = is_internalTransaction(current_transaction, csv)
        if not internalTrans_tf:
            transactions_compiled = externalTransactions_append(
                current_transaction, csv, transactions_compiled)

        # Work on Internal transactions
        elif internalTrans_tf:
            nearest_duplicate = determine_internalTransactions(
                current_transaction, csv)

            transactions_compiled = internalTransaction_append(
                current_transaction, nearest_duplicate, csv,
                transactions_compiled)

##########################################################################
#-----------PUTTING DATA IN GNUCASH--------------------------------------
##########################################################################
if write_to_book:
    book = piecash.open_book(path_to_Book.as_posix(), readonly=False)

    if len(book.commodities) == 1:
        currency = book.commodities[0]

    try:
        book.accounts(name='Uncategorized')
    except:
        a1 = piecash.Account("Uncategorized", "EXPENSE", currency, parent=book.root_account)
        book.save()

    for index, transaction in transactions_compiled.iterrows():
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


            