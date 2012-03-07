# EVE Cache Trade Finder v0.2
# Copyright (C)2012 by Eirik Krogstad
# Requires the Python libraries bottle and reverence
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
timelimit = 24        # hours
cargolimit = 10000    # m3
bytrip = True         # get results by profit per trip
byprofit = False      # get results by total profit
# lowsecfilter = False  # accounting skill level
# accounting = 0        # accounting skill level

def realtime(s):
    return (time.time() - ((s - 116444736000000000) / 10000000)) / 3600

def iskstring(isk):
    return '{0:,.2f} ISK'.format(isk)

@route('/')
@route('/index.html')
def index():
    global profitlimit, timelimit, cargolimit

    profitlimit = int(request.query.profitlimit or profitlimit)
    timelimit = int(request.query.timelimit or timelimit)
    cargolimit = int(request.query.cargolimit or cargolimit)

    output = ''
    sell = list()
    buy = list()
    counter = 0

    for key, obj in cmc.iteritems():
        if key[1] == 'GetOrders' and realtime(obj['used']) < timelimit:
            item = cfg.invtypes.Get(key[3])
            region = cfg.evelocations.Get(key[2])
            orders = obj['lret']
            # 0 = sell orders, 1 = buy orders
            for row in orders[0]:
                sell.append([row.typeID, [row.price, row.volRemaining, row.stationID, key[2]]])
            for row in orders[1]:
                buy.append([row.typeID, [row.price, row.volRemaining, row.stationID, key[2]]])

    output += '<html>\n'
    output += '<head>\n'
    output += '<title>EVE Python Cache Trade Finder</title>\n'
    output += '<style>\n'
    output += 'body { background: #111; color: #ddd; font: 12px/18px Arial, sans-serif }\n'
    output += 'a { color: #ada }\n'
    output += 'input { width: 70px; padding: 0 2px; background: inherit; color: inherit; border: 1px solid #ddd }\n'
    output += 'input[type="text"] { text-align: right }\n'
    output += 'table, td { border: 0; padding: 0 5px 0 0; font: inherit }\n'
    output += '</style>\n'
    output += '</head>\n'
    output += '<body>\n'
    output += '<script>CCPEVE.requestTrust("http://localhost")</script>\n'
    if not request.headers.get('Eve-Trusted') == 'Yes':
        output += '<strong style="color: #faa">Please make this site trusted, this will give you better links and ability to calculate routes.</strong> <br><br>\n'
    output += '<form action="/" method="get">\n'
    output += '<table>\n'
    output += '<tr><td>Profit limit is</td><td><input type="text" name="profitlimit" value="%i"> ISK</td></tr>\n' % profitlimit
    output += '<tr><td>Cache time limit is</td><td><input type="text" name="timelimit" value="%i"> hours</td></tr>\n' % timelimit
    output += '<tr><td>Cargo limit is</td><td><input type="text" name="cargolimit" value="%i"> m<sup>3</sup></td></tr>\n' % cargolimit 
    output += '<tr><td></td><td><input type="submit" value="Reload"></td></tr>\n'
    output += '</table>\n'
    output += '</form>\n'

    for stype, sdata in sell:
        for btype, bdata in buy:
            if stype == btype:
                # 0 = price, 1 = volremaining, 2 = stationid, 3 = regionid
                if bdata[0] > sdata[0]:
                    item = cfg.invtypes.Get(stype)
                    tradable = min(sdata[1], bdata[1])
                    diff = bdata[0] - sdata[0]
                    profit = tradable * diff
                    tripprofit = min(tradable, (cargolimit/item.volume)) * diff
                    if (bytrip and tripprofit > profitlimit) or (byprofit and profit > profitlimit):
                        output += '<strong><a href="javascript:CCPEVE.showMarketDetails(%i)">%s</a></strong> <br>\n' % (stype, item.name)
                        output += 'Source: <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (sdata[2], cfg.evelocations.Get(sdata[2]).name, \
                                     cfg.evelocations.Get(sdata[3]).name)                    
                        output += 'Destination: <a href="javascript:CCPEVE.showInfo(3867, %i)">%s</a>, %s <br>\n' % \
                                    (bdata[2], cfg.evelocations.Get(bdata[2]).name, \
                                     cfg.evelocations.Get(bdata[3]).name)
                        output += '%i units tradable (%i for sale -> %i bought) <br>\n' % (tradable, sdata[1], bdata[1])
                        output += 'Sell price: %s <br>\n' % iskstring(sdata[0])
                        output += 'Buy price: %s <br>\n' % iskstring(bdata[0])
                        output += '<strong>Profit per trip: %s</strong> <br>\n' % iskstring(tripprofit)
                        output += '<strong>Potential profit: %s</strong> <br>\n' % iskstring(profit)
                        output += '<br>\n'
                        counter += 1
    if counter == 0:
        output += 'No trades found.\n'

    output += '</body>\n'
    output += '</html>'
    return output

run(host='localhost', port=80, reloader=True)
