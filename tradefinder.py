# EVE Cache Trade Finder v0.3
# Copyright (C) 2012 by Eirik Krogstad
# Requires the Python libraries Bottle and Reverence
# Bottle: https://github.com/defnull/bottle
# Reverence: https://github.com/ntt/reverence

import time
from reverence import blue
from bottle import route, request, run

EVEROOT = 'C:\Program Files (x86)\EVE Online'

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()
cachemgr = eve.getcachemgr()
cmc = cachemgr.LoadCacheFolder('CachedMethodCalls')

profitlimit = 1000000 # ISK
timelimit = 24        # hours
cargolimit = 10000    # m3
bytrip = True         # get results by profit per trip
byprofit = False      # get results by total profit
accounting = 0        # accounting skill level
cutoff = 0.1          # factor of highest/lowest price where the indexing gets cut off (0.1 = 10 %)
                      # lower cutoff gives greater speed, but you may miss some trades
                      # higher cutoff may take a long time with a large cache

def realtime(s):
    return (time.time() - ((s - 116444736000000000) / 10000000)) / 3600

def iskstring(isk):
    return '{0:,.2f} ISK'.format(isk)

head = '''<!doctype html>
<html>
<head>
<title>EVE Cache Trade Finder</title>
<style>
body { background: #111; color: #ddd; font: 12px/18px Arial, sans-serif }
a { color: #fa6 }
input, select { width: 70px; padding: 0 2px; background: #333; color: #fff; border: 1px solid #ddd; -webkit-box-sizing: border-box }
.right, input[type="text"] { text-align: right; }
select { padding: 0 0 0 37px }
label, span.right { float: left; min-width: 120px; }
label, span.total { font-weight: bold }
form label { position: relative; top: 3px }
</style>
</head>
'''

@route('/')
@route('/index.html')
def index():
    global profitlimit, timelimit, cargolimit, accounting

    profitlimit = int(request.query.profitlimit or profitlimit)
    timelimit = int(request.query.timelimit or timelimit)
    cargolimit = int(request.query.cargolimit or cargolimit)
    accounting = int(request.query.accounting or accounting)

    sell = list()
    buy = list()
    for key, obj in cmc.iteritems():
        if key[1] == 'GetOrders' and realtime(obj['runid']) < timelimit:
            item = cfg.invtypes.Get(key[3])
            region = cfg.evelocations.Get(key[2])
            lowest = 1000000000000
            highest = 0
            # 0 = sell orders, 1 = buy orders
            for row in obj['lret'][0]:
                lowest = min(row.price, lowest)
                if row.price < lowest * (1 + cutoff):
                    sell.append([row.typeID, [row.price, row.volRemaining, row.stationID, key[2]]])
            for row in obj['lret'][1]:
                highest = max(row.price, highest)
                if row.price > highest * (1 - cutoff):
                    buy.append([row.typeID, [row.price, row.volRemaining, row.stationID, key[2]]])

    output = head
    output += '<body>\n'
    output += '<script>CCPEVE.requestTrust("http://localhost")</script>\n'
    if not request.headers.get('Eve-Trusted') == 'Yes':
        output += '<strong style="color: #f66">Please make this site is trusted, this will give you better links and ability to calculate routes.</strong> <br><br>\n'
    output += '<form action="/" method="get">\n'
    output += '<label>Profit limit </label><input type="text" name="profitlimit" value="%i"> ISK<br>\n' % profitlimit
    output += '<label>Cache time limit </label><input type="text" name="timelimit" value="%i"> hours<br>\n' % timelimit
    output += '<label>Cargo limit </label><input type="text" name="cargolimit" value="%i"> m&#179;<br>\n' % cargolimit
    accountingoptions = ''
    for i in range(6):
        accountingoptions += '<option value="%i"%s>%i</option>' % (i, (' selected="selected"' if accounting == i else ''), i)
    taxlevel = (1 - (accounting * 0.1)) * 0.01
    output += '<label>Accounting skill </label><select name=accounting>%s</select> (tax level %.2f %%)<br>\n' % (accountingoptions, taxlevel * 100)
    output += '<label>&nbsp;</label><input type="submit" value="Reload"><br>\n'
    output += '</form> <br>\n'

    counter = 0
    for stype, sdata in sell:
        for btype, bdata in buy:
            if stype == btype:
                # 0 = price, 1 = volremaining, 2 = stationid, 3 = regionid
                if bdata[0] > sdata[0]:
                    item = cfg.invtypes.Get(stype)
                    diff = bdata[0] - sdata[0]
                    tradable = min(sdata[1], bdata[1])
                    movable = min(tradable, int(cargolimit/item.volume))
                    investment = tradable * sdata[0]
                    triptax = movable * bdata[0] * taxlevel
                    tripprofit = (movable * diff) - triptax
                    tax = tradable * bdata[0] * taxlevel
                    profit = (tradable * diff) - tax
                    
                    if (bytrip and tripprofit > profitlimit) or (byprofit and profit > profitlimit):
                        output += '<strong><a href="javascript:CCPEVE.showMarketDetails(%i)">%s</a></strong> <br>\n' % (stype, item.name)
                        output += '<label>From:</label> <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (sdata[2], cfg.evelocations.Get(sdata[2]).name, cfg.evelocations.Get(sdata[3]).name)                    
                        output += '<label>To:</label> <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (bdata[2], cfg.evelocations.Get(bdata[2]).name, cfg.evelocations.Get(bdata[3]).name)
                        output += '<label>Units tradable:</label><span class="right">%i (%i -> %i)</span> <br>\n' % (tradable, sdata[1], bdata[1])
                        output += '<label>Units per trip:</label><span class="right">%i (%.2f m&#179; each)</span> <br>\n' % (movable, item.volume)
                        output += '<label>Sell price:</label><span class="right">%s</span> <br>\n' % iskstring(sdata[0])
                        output += '<label>Buy price:</label><span class="right">%s</span> <br>\n' % iskstring(bdata[0])
                        output += '<label>Investment:</label><span class="right">%s</span> <br>\n' % iskstring(investment)
                        output += '<label>Total tax:</label><span class="right">%s</span> <br>\n' % iskstring(tax)
                        output += '<label>Profit per trip:</label><span class="right total">%s</span> <br>\n' % iskstring(tripprofit)
                        output += '<label>Potential profit:</label><span class="right total">%s</span> <br>\n' % iskstring(profit)
                        output += '<br>\n'
                        counter += 1
    if counter == 0:
        output += 'No trades found.\n'

    output += '</body>\n'
    output += '</html>'

    return output

run(host='localhost', port=80, reloader=True)
