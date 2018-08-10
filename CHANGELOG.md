# Changelog

## Unreleased

## 0.3.2 - 2018-08-10

### Fixed
- (#11) Dates are now added correctly to GNUCash book

### Changed
- Removed common placeholder accounts from translation.json

## 0.3.1 - 2018-08-09

### Fixed
- (#11) Logging simplified, no longer hampers performance.

## 0.3.0 - 2018-08-09

### Added
- Logging is now a functionality!

## 0.2.5 - 2018-08-09

### Added
- Docstrings for every function
- Added `dfgui` section to `example/example.py`

### Fixed
- "IGNORE" functionality is now working
- Corrected `example/translation.json` entry for Clothing

## 0.2.4 - 2018-07-02

### Added 
- translations.json now has a "IGNORE" category options
- README has better documentation on using translations.json
- Compiled Examples files into example folder

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
