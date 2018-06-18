# csv2cash
Repo for importing CSV files to GNUCash with some preprocessing built in.

## What does it do?
### It takes your raw transfer data and compiles it into transactions
A transfer is simply half of a transaction in double-entry bookkeeping (which GNUCash uses). So if you move money from Bank Account A to Bank Account B, then you have two transfer records; one from Bank Account A saying XXX money was withdrawn and one from Bank Account B saying XXX money was deposited. 

In Mint for example, if you export a CSV of all your transfer data, it will keep each transfer separate from the other, even though they are directly related and should be viewed as a single transaction. This script finds the separate transfers, figures out which ones correspond to each other, and puts their data together

### Translates your CSV categories into a GNUCash account
Say your CSV has a category system attached to each transfer and you want that organization to be transferred into Mint without having to go one-by-one through every transfer and label them. This will do that by setting up the `translation.json` dictionary, which will take a transfer that is under a given category, and place it in the corresponding GNUCash account.

## How to Use:
### 1. Make your inputs
There is a section in the `main.py` script called `INPUTS`. Here you will enter in the path to the CSV of your raw transfer data, the GNUCash book you want to edit, and the translation JSON.

You should already have filled out the `translation.json` at this point.

###2. Run the Script!
Once you run the script, it will do all the work and edit your GNUCash book.

## Note
Currently requires the use of a development version of `piecash` to work with GNUCash 3.X. You can install the new version currently (2018-06-18) through pip: 

`pip install git+https://github.com/sdementen/piecash.git@feature/py3-gnucash3`
