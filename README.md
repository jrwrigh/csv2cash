# csv2cash
Python package for importing CSV files to GNUCash with some preprocessing built in.

## What does it do?
### It takes your raw transfer data and compiles it into transactions
A transfer is simply half of a transaction in [double-entry bookkeeping](https://en.wikipedia.org/wiki/Double-entry_bookkeeping_system) ([which GNUCash uses](https://www.gnucash.org/features.phtml#main-feat)). So if you move money from Bank Account A to Bank Account B, then you have two transfer records, one for each Account. One from Bank Account A saying $XXX money was withdrawn and one from Bank Account B saying $XXX money was deposited. In GNUCash, though, these two transfers are viewed as a single transaction: $XXX was moved from Bank Account A --> Bank Account B.

In Mint for example, if you export a CSV of all your transfer data, it will keep each transfer separate from the other, even though they are directly related and should be viewed as a single transaction. This package finds the separate transfers, figures out which ones correspond to each other, and puts their data together

### Translates your CSV categories into a GNUCash account
Say your CSV has a category system attached to each transfer and you want that organization to be transferred into Mint without having to go one-by-one through every transfer and label them. This will do that by setting up the `translation.json` dictionary, which will take a transfer that is under a given category, and place it in the corresponding GNUCash account.

Use the `get_uncat_transfers` function to view any transactions that haven't been categorized. This can be useful to determine what translations you still need to add to `translations.json`. You can also use `write_account_list` to create a text file of all the accounts in a GNUCash book, this way you don't have to keep your GNUCash book open the whole time!

## Requirements
- pandas
- piecash (see [note](#note) below about versioning)
- Verified for Python 3.6, though should work for other versions

# Instructions:

See examples in `./example` for how to use the module effectively. 

## Structure:
The module takes data from a .csv file, translates information (such as category and account names) by referencing the `translations.json` dictionary, combines internal transfers (ie. moving money from savings account to checking account), and puts the translated data into the GNUCash Book of your choosing.

## How to Use?:
### 1. Create your `translations.json`
This stores the information that will be translated from your csv to the GNUCash book. If a key:value pair does not match up with a category or account name in the csv, it will be placed into an "Uncategorized" setting.

### Pre-2. Run `get_compiled_transactions`
I recommend doing this to make sure that all the transactions look ok. I recommend using `dfgui` as a way to view the DataFrames to make sure everything is looking right.

### 2. Run `do_csv2cash`!
This function will do all the work and edit your GNUCash book. If you want to, you can go step-by-step by using the individual commands at each step. 

## About `translations.json`:

### Structure:
The `translations.json` file has two dictionaries called "Categories" and "Accounts" that stores translations for category names and account names, respectively.

The "key" in each key:value pair is the string that will match the csv, while the "value" is the string that matches the name in the GNUCash Book. 

If the "value" is set to `"IGNORE"`, then that transfer (the row of the csv) will be ignored and will not be passed through to the rest of the functions.

Below is an example of a `translations.json` file:

```json
{
    "Categories":{
        "Mortgage & Rent" : "Rent",
        "Sporting Goods" : "Hobbies",
        "Music" : "Music/Movies",
        "Uncategorized" : "Uncategorized",
        "Unwanted Transfers" : "IGNORE"
    },
    "Accounts":{
        "BofA Core Checking" : "Checking Account",
        "Regular Savings" : "Savings Account",
        "Cash" : "Cash in Wallet",
        "Roth Contributory IRA" : "Market Index",
        "Uncategorized" : "Uncategorized"
    }
}
```

### Creating
A few tools have been created in order to assist with the creation of the `translations.json` file. They are `get_uncat_transfers` and `write_account_list`. 

`get_uncat_transfer` will return a pandas DataFrame will all the transfers who's modified category name is "Uncategorized" (which is the default if no applicable key:value pair is given). This can be viewed using `dfgui` to see what transfers still need translations. `dfgui` also has several helpful sorting features built-in.

`write_account_list` writes a text file with the account fullnames (see `piecash` documentation for account fullname definition) of the GNUCash Book specified. This gives a simple way to view what options you have to translate your transfers to.

## Note:

Currently requires the use of a development version of `piecash` to work with GNUCash 3.X. You can install the new version currently (2018-06-18) through pip: 

`pip install git+https://github.com/sdementen/piecash.git@feature/py3-gnucash3`
