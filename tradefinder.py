# EVE Cache Trade Finder v0.4
# Copyright (C) 2012 by Eirik Krogstad
# Requires the Python libraries Bottle and Reverence
# Bottle: https://github.com/defnull/bottle
# Reverence: https://github.com/ntt/reverence

import time
from reverence import blue
from bottle import route, request, run

EVEROOT = 'C:\Program Files (x86)\CCP\EVE'

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()
cachemgr = eve.getcachemgr()
cmc = cachemgr.LoadCacheFolder('CachedMethodCalls')

profitlimit = 1000000 # ISK
timelimit = 4         # hours
cargolimit = 1000     # m3
accounting = 0        # accounting skill level
sortby = 0            # selected sort option, see list below
sortstrings = ['Trip profit', 'Total profit']

resultlimit = 1000    # limit for total number of results

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
    input, select { width: 85px; padding: 0 2px; background: #333; color: #fff; border: 1px solid #ddd; -webkit-box-sizing: border-box }
    .right, input[type="text"] { text-align: right }
    select { padding: 0 }
    label, span.right { float: left; min-width: 120px }
    label, span.total { font-weight: bold }
    form label { position: relative; top: 3px }
</style>
</head>
'''

@route('/')
@route('/index.html')
def index():
    global profitlimit, timelimit, cargolimit, accounting, sortby

    profitlimit = int(request.query.profitlimit or profitlimit)
    timelimit = int(request.query.timelimit or timelimit)
    cargolimit = int(request.query.cargolimit or cargolimit)
    accounting = int(request.query.accounting or accounting)
    sortby = int(request.query.sortby or sortby)
    taxlevel = (1 - (accounting * 0.1)) * 0.01

    sell = {}
    buy = {}
    for key, obj in cmc.iteritems():
        if key[1] == 'GetOrders' and realtime(obj['runid']) < timelimit:
            item = cfg.invtypes.Get(key[3])
            region = cfg.evelocations.Get(key[2])
            # 0 = sell orders, 1 = buy orders
            for row in obj['lret'][0]:
                if row.typeID in sell:
                    sell[row.typeID].append(row)
                else:
                    sell[row.typeID] = [row]
            for row in obj['lret'][1]:
                if row.typeID in buy:
                    buy[row.typeID].append(row)
                else:
                    buy[row.typeID] = [row]

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
    sortoptions = ''
    for i in range(2):
        sortoptions += '<option value="%i"%s>%s</option>' % (i, (' selected="selected"' if sortby == i else ''), sortstrings[i])
    output += '<label>Accounting skill </label><select name=accounting>%s</select> (tax level %.2f %%)<br>\n' % (accountingoptions, taxlevel * 100)
    output += '<label>Sort by </label><select name=sortby>%s</select><br>\n' % (sortoptions)
    output += '<label>&nbsp;</label><input type="submit" value="Reload"><br>\n'
    output += '</form> <br>\n'

    results = []
    for typeid, sellitems in sell.iteritems():
        for sellitem in sellitems:
            for buyitem in buy.get(typeid, []):
                if buyitem.price > sellitem.price:
                    
                    item = cfg.invtypes.Get(typeid)
                    diff = buyitem.price - sellitem.price
                    tradable = min(sellitem.volRemaining, buyitem.volRemaining)
                    movable = min(tradable, int(cargolimit/item.volume))
                    investment = tradable * sellitem.price
                    triptax = movable * buyitem.price * taxlevel
                    tripprofit = (movable * diff) - triptax
                    tax = tradable * buyitem.price * taxlevel
                    profit = (tradable * diff) - tax
                    
                    if len(results) < resultlimit and (sortby == 0 and tripprofit > profitlimit) or (sortby == 1 and profit > profitlimit):
                        result = ''
                        result += '<strong><a href="javascript:CCPEVE.showMarketDetails(%i)">%s</a></strong> <br>\n' % (typeid, item.name)
                        result += '<label>From:</label> <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (sellitem.stationID, cfg.evelocations.Get(sellitem.stationID).name, cfg.evelocations.Get(sellitem.regionID).name)                    
                        result += '<label>To:</label> <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (buyitem.stationID, cfg.evelocations.Get(buyitem.stationID).name, cfg.evelocations.Get(buyitem.regionID).name)
                        result += '<label>Units tradable:</label><span class="right">%i (%i -> %i)</span> <br>\n' % (tradable, sellitem.volRemaining, buyitem.volRemaining)
                        result += '<label>Units per trip:</label><span class="right">%i (%.2f m&#179; each)</span> <br>\n' % (movable, item.volume)
                        result += '<label>Sell price:</label><span class="right">%s</span> <br>\n' % iskstring(sellitem.price)
                        result += '<label>Buy price:</label><span class="right">%s</span> <br>\n' % iskstring(buyitem.price)
                        result += '<label>Investment:</label><span class="right">%s</span> <br>\n' % iskstring(investment)
                        result += '<label>Total tax:</label><span class="right">%s</span> <br>\n' % iskstring(tax)
                        result += '<label>Profit per trip:</label><span class="right total">%s</span> <br>\n' % iskstring(tripprofit)
                        result += '<label>Potential profit:</label><span class="right total">%s</span> <br>\n' % iskstring(profit)
                        result += '<br>\n'
                        results.append([tripprofit, profit, result])

    if len(results) == 0:
        output += 'No trades found.\n'
    else:
        for result in sorted(results, key = lambda result: result[sortby], reverse=True):
            output += result[2]

    output += '</body>\n'
    output += '</html>'

    return output

run(host='localhost', port=80, reloader=True)
