# EVE Cache Trade Finder v0.7 #

Copyright (C) 2012 by Eirik Krogstad

Licenced under the MIT License, see http://www.opensource.org/licenses/MIT

I played a bit of EVE Online and got into trading. I found the [EVE-Central](http://eve-central.com/) Trade Finder to be a bit unreliable, and [NavBot](http://code.google.com/p/navbot/) to be slow and exporting market logs tedious.

This script will scan your EVE cache using [Reverence](https://github.com/ntt/reverence), find potential trades, and output a web page with the results to `http://localhost` using [Bottle](https://github.com/defnull/bottle), which can then be opened in the in-game browser.

Donations to `Stella Singularity` accepted :)

## Usage: ##
1. Make sure you have Reverence and Bottle installed (bottle.py can be placed in the same directory as this, for Reverence, try an [installer](https://github.com/ntt/reverence/downloads))
2. Edit the script with the path to your EVE installation
3. View Market Details for several items in EVE, preferably in different regions. You only need to visit the market page. See also point 6.
4. Start the script with `python tradefinder.py`
5. Visit `http://localhost` from the in-game browser. Accepting localhost as trusted will give you better links and ability to calculate jumps. Filled orders will be removed as the page and cache is updated.
6. Optionally use the Automated Market Scanner to have the script browse the market for you. The market screen will take focus every three seconds, so do it while docked or travelling safely. The delay is required to make sure EVE does not deny the JavaScript calls, so the scan can take some time.

## Changelog: ##
* v0.7 - Added system security indicators, market scanner fixes
* v0.6 - Added calculation of jump lengths, sort by profit per jump
* v0.5 - Added Automated Market Scanner
* v0.4 - Massive performance increase, ability to sort by trip profit or total profit
* v0.3 - Cleaned up HTML, added tax, price limit for indexing
* v0.2 - First version to use Bottle and the in-game browser. Limited feature set, no sorting of trades.
* v0.1 - Initial version writes trades to standard output

