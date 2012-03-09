# EVE Cache Trade Finder v0.4 #

Copyright (C) 2012 by Eirik Krogstad

Licenced under the MIT License, see http://www.opensource.org/licenses/MIT

I played a bit of EVE Online and got into trading. I found the [EVE-Central](http://eve-central.com/) Trade Finder to be a bit unreliable, and [NavBot](http://code.google.com/p/navbot/) to be slow and exporting market logs tedious.

This script will scan your EVE cache using [Reverence](https://github.com/ntt/reverence), find potential trades, and output a web page to _http://localhost_ using [Bottle](https://github.com/defnull/bottle), which can then be opened in the in-game browser.

Accepting localhost as trusted will only give you better links as of now, but will be useful for calculating routes and number of jumps in the future.

## Usage: ##
1. Make sure you have Reverence and Bottle installed
2. Edit the script with the path to your EVE installation
3. View Market Details for a lot of items in EVE, preferably in different regions. You only need to visit the market page.
4. Start the script with `python tradefinder.py`
5. Visit _http://localhost_ from the in-game browser

## Changelog: ##
* 0.4 - Massive performance increase, ability to sort by trip profit or total profit
* 0.3 - Cleaned up HTML, added tax, price limit for indexing.
* 0.2 - First version to use Bottle and the in-game browser. Limited feature set, no sorting of trades.
* 0.1 - Initial version writes trades to standard output

