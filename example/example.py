import csv2cash
from pathlib import Path
# import dfgui # <- for DF visualization

path_to_CSV = Path.cwd() / 'transactions_testPUBLIC.csv'
path_to_Book = Path.cwd() / 'test.gnucash'
path_to_translationJSON = Path.cwd() / 'translations.json'

# # For checking the translations
# transfer_uncat = csv2cash.get_uncat_transfers(path_to_CSV,
#                                               path_to_translationJSON)
# dfgui.show(transfer_uncat)

csv2cash.do_csv2cash(path_to_Book, path_to_CSV, path_to_translationJSON)