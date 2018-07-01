# Changelog

## Unreleased

## 0.2.3 - 2018-07-01

### Added
- `write_account_list` was added. This will write the fullname of accounts listed in GNUCash book

## 0.2.2 - 2018-06-18

### Added
- `get_uncat_transfers` was added. This is a fix of v0.2.1, which should have have presented a filtered DataFrame of the transfers rather than a filtered version of the transactions

### Removed
- `get_uncat_transactions` was removed

## 0.2.1 - 2018-06-18

### Added
- `get_uncat_transactions` to easily view what translations didn't have a translation that was applicable for them in `translations.json`.

## 0.2.0 - 2018-06-18

### Added
- Put everything into a single package
- Added `example.py` to show the new functionality
- Instructions added to direct a step-by-step approach


## 0.1.0 - 2018-06-18

### Added
- Current will take CSV from Mint, pre-process the data, then add it to the GNUCash book
- All inputs are given in the single script itself
- Translations for the preprocessing are in `translations.json`