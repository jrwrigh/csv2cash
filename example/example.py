import logging
logging.basicConfig(
    filename='csv2cash.log',
    level=logging.INFO,
    format=
    '%(asctime)s, %(levelname)-8s [%(filename)s:%(module)s:%(funcName)s:%(lineno)d] %(message)s'
)

from pathlib import Path
# Get path for csv2cash if run inside this directory structure
import sys
import os
scriptdir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, scriptdir.parents[0].as_posix())

import csv2cash
# import dfgui # <- for DF visualization

path_to_CSV = scriptdir / 'transactions_testPUBLIC.csv'
path_to_Book = scriptdir / 'test.gnucash'
path_to_translationJSON = scriptdir / 'translations.json'

# # For checking the translations
# transfer_uncat = csv2cash.get_uncat_transfers(path_to_CSV,
#                                               path_to_translationJSON)
# dfgui.show(transfer_uncat)

csv2cash.do_csv2cash(path_to_Book, path_to_CSV, path_to_translationJSON)