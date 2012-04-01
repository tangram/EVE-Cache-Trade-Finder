# EVE Cache Trade Finder v0.8
# Copyright (C) 2012 by Eirik Krogstad
# Licenced under the MIT License, see http://www.opensource.org/licenses/MIT
# Requires the Python libraries Bottle and Reverence
# Bottle: https://github.com/defnull/bottle
# Reverence: https://github.com/ntt/reverence

import time
from reverence import blue
from bottle import route, request, run
from collections import deque
import textwrap
import data
import eveapi

EVEROOT = 'C:\Program Files (x86)\CCP\EVE'

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()
cachemgr = eve.getcachemgr()

API_KEYID = 123456
API_VCODE = "longalphanumericapiverificationcodegoeshere"

api = eveapi.EVEAPIConnection()
auth = api.auth(keyID=API_KEYID, vCode=API_VCODE)

# initial configuration
profitlimit = 1000000 # ISK
timelimit = 24        # hours
cargolimit = 1000     # m3
accounting = 0        # accounting skill level
sortby = 0            # selected sort option, see list below

SORTSTRINGS = ['Trip profit', 'Total profit', 'Jump profit']
RESULTLIMIT = 100     # limit for total number of results

def real_age(t):
    '''Time since an EVE timestamp in hours'''
    return (time.time() - ((t - 116444736000000000) / 10000000)) / 3600

def isk_string(isk):
    '''Convert a number to a string on the form "1,000.00 ISK"'''
    return '{0:,.2f} ISK'.format(isk)

def sec_class(sec):
    '''Convert security float to a letter for link coloring'''
    return chr(int(75 - (sec * 10))) if sec > 0 else 'X'

def breadth_first_search(graph, start):
    '''General breadth first search generator'''
    queue, enqueued = deque([(None, start)]), set([start])
    while queue:
        parent, n = queue.popleft()
        yield parent, n
        new = set(graph[n]) - enqueued
        enqueued |= new
        queue.extend([(n, child) for child in new])

def shortest_path(graph, start, end):
    '''Finds the shortest path in a set of paths'''
    if start == 0 or end == 0:
        return []
    paths = {None: []}
    for parent, child in breadth_first_search(graph, start):
        paths[child] = paths[parent] + [child]
        if child == end:
            return paths[child]
    return []

def path_length(path):
    '''Get the length of a path'''
    if path:
        return len(path) - 1
    return 0

def index_market(timelimit=timelimit):
    '''Index sell and buy data'''
    cmc = cachemgr.LoadCacheFolder('CachedMethodCalls')
    sell = {}
    buy = {}
    for key, obj in cmc.iteritems():
        if key[1] == 'GetOrders' and real_age(obj['version'][0]) < timelimit:
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
    return sell, buy

head = '''
<!doctype html>
<html>
<head>
<title>%s</title>

<style>
    body { background: #111; color: #ddd; font: 12px/18px Arial, sans-serif }
    h1 { font-size: 2em }
    h2 { font-size: 1.5em; color: #9f5 }
    h3 { font-size: 1.3em; color: #bd5 }
    h4 { font-size: 1.2em; color: #db5 }
    h5 { font-size: 1.1em; color: #f95 }
    h1, h2, h3, h4, h5 { line-height: 1em; margin: 0.5em 0 }
    h1 { background: #333; padding: 0.25em }
    h2.item { clear: both; margin: 0.5em 0; font-size: 1.2em }
    a, .item { color: #cce; text-decoration: none }
    a:hover { text-decoration: underline }
    #links a, #links #current { font-size: 1.25em; font-weight: bold; margin-right: 1em }
    #links #current { color: #aaa }
    input, select, button { width: 115px; padding: 0 2px; margin-right: 0.5em;
                            background: #333; color: #fff; 
                            border: 1px solid #ddd; -webkit-box-sizing: border-box }
    table { margin: 0 0 1em }
    td, th { padding-right: 2em }
    th { text-align: left }
    .ralign { text-align: right }
    #scancheck { position: relative; top: 2px }
    .stats, input[type="text"] { text-align: right }
    .labels, .stats { float: left; min-width: 120px }
    .labels { clear: left; margin: 0 0 2em }
    .stats { clear: right }
    .labels label { display: block }
    label, span.total { font-weight: bold }
    form label { margin: 2px 0 5px }
    select { padding: 0 }
    #scan { width: 150px; margin-right: 1em }
    #progress { border: 1px solid #ddd; height: 10px; width: 150px; top: 1px;
                display: inline-block; position: relative; margin: 0.5em 1em 0 0 }
    #bar { background: #666; height: 10px; width: 0; display: block;
           position: relative; overflow: hidden }
    input[type="checkbox"] { width: 15px }
    .floater { margin: 0 2em 2em 0; float: left; }
    .checker { min-width: 200px }
    .checkchecker { font-size: 10px; margin-left: 3px }
    .checkchecker input[type="checkbox"] { height: 9px; width: 9px; padding: 0 }
    .A { color: #5f5 }
    .B { color: #7f5 }
    .C { color: #9f5 }
    .D { color: #bf5 }
    .E { color: #df5 }
    .F { color: #ff5 }
    .G { color: #fd5 }
    .H { color: #fb5 }
    .I { color: #f95 }
    .J { color: #f75 }
    .X { color: #f55 }
</style>
'''
headend = '</head>'

@route('/')
def index():
    '''Main page; Trade finder'''
    global profitlimit, timelimit, cargolimit, accounting, sortby

    # set user variables from url string
    profitlimit = int(request.query.profitlimit or profitlimit)
    timelimit = int(request.query.timelimit or timelimit)
    cargolimit = int(request.query.cargolimit or cargolimit)
    accounting = int(request.query.accounting or accounting)
    sortby = int(request.query.sortby or sortby)
    taxlevel = (1 - (accounting * 0.1)) * 0.01

    sell, buy = index_market(timelimit)

    output = head % 'Trade finder' + headend
    # settings section
    output += textwrap.dedent('''
        <body>
        <div id="links">
        <span id="current">Trade finder</span>
        <a href="/scan">Automated market scanner</a>
        <a href="/orderwatch">Order watch</a>
        </div>
        <h1>Trade finder</h1>
        ''')

    if not request.headers.get('Eve-Trusted') == 'Yes':
        output += '<script>CCPEVE.requestTrust("http://localhost")</script>'
    
    output += textwrap.dedent('''
        <form action="/" method="get">
        <div class="labels">
        <label>Profit limit</label>
        <label>Cache time limit</label>
        <label>Cargo limit</label>
        <label>Accounting skill</label>
        <label>Sort by</label>
        <label>&nbsp;</label>
        </div>
        <input type="text" name="profitlimit" value="%i"> ISK<br>
        <input type="text" name="timelimit" value="%i"> hours<br>
        <input type="text" name="cargolimit" value="%i"> m&#179;<br>''' 
        % (profitlimit, timelimit, cargolimit))
    
    accountingoptions = ''
    for i in range(6):
        selected = ' selected="selected"' if accounting == i else ''
        accountingoptions += ('<option value="%i"%s>%i</option>' 
                              % (i, selected, i))
    
    sortoptions = ''
    for i in range(len(SORTSTRINGS)):
        selected = ' selected="selected"' if sortby == i else ''
        sortoptions += ('<option value="%i"%s>%s</option>' 
                        % (i, selected, SORTSTRINGS[i]))
    
    output += textwrap.dedent('''
        <select name=accounting>
        %s
        </select> (tax level %.2f %%)<br>
        <select name=sortby>
        %s
        </select><br>
        <input type="submit" value="Reload"><br>
        </form>
        ''' % (accountingoptions, taxlevel * 100, sortoptions))

    currentsystem = int(request.headers.get('Eve-SolarSystemID') or 0)

    # search for trades
    results = []
    for typeid, sellitems in sell.iteritems():
        for sellitem in sellitems:
            for buyitem in buy.get(typeid, []):
                if buyitem.price > sellitem.price:
                    
                    # calculate trade data
                    item = cfg.invtypes.Get(typeid)
                    diff = buyitem.price - sellitem.price
                    tradable = min(sellitem.volRemaining, buyitem.volRemaining)
                    movable = min(tradable, int(cargolimit/item.volume))
                    investment = tradable * sellitem.price
                    triptax = movable * buyitem.price * taxlevel
                    tripprofit = (movable * diff) - triptax        
                    tax = tradable * buyitem.price * taxlevel
                    profit = (tradable * diff) - tax

                    if sellitem.stationID == buyitem.stationID:
                        tripprofit = profit
                    
                    if (len(results) < RESULTLIMIT and
                       (sortby == 0 and tripprofit > profitlimit) or
                       (sortby == 1 and profit > profitlimit) or
                       (sortby == 2 and tripprofit > profitlimit)):
                        # add result to result list
                        # further calculations
                        sellsec = data.security[sellitem.solarSystemID]
                        buysec = data.security[buyitem.solarSystemID]

                        path1 = shortest_path(data.jumps, 
                                              currentsystem, 
                                              sellitem.solarSystemID)
                        path2 = shortest_path(data.jumps, 
                                              sellitem.solarSystemID, 
                                              buyitem.solarSystemID)
                        
                        lowsecwarning = ''
                        for system in path1 + path2:
                            if data.security[system] < 0.5:
                                lowsecwarning = '<span class="X">(through lowsec)</span>'
                        
                        jumpsfromcurrent = path_length(path1)
                        jumpsfromsell = path_length(path2)
                        totaljumps = jumpsfromcurrent + jumpsfromsell
                        jumpprofit = tripprofit / (totaljumps + 1)

                        smd = 'javascript:CCPEVE.showMarketDetails'
                        si = 'javascript:CCPEVE.showInfo'

                        result = ('<h2 class="item"><a href="%s(%i)">%s</a></h2>'
                                  % (smd, typeid, item.name))

                        result += textwrap.dedent('''
                            <div class="labels">
                            <label>From:</label>
                            <label>To:</label>
                            <label>Jumps:</label>
                            <label>Units tradable:</label>
                            <label>Units per trip:</label>
                            <label>Sell price:</label>
                            <label>Buy price:</label>
                            <label>Investment:</label>
                            <label>Total tax:</label>
                            <label>Profit per jump:</label>
                            <label>Profit per trip:</label>
                            <label>Potential profit:</label>
                            </div>
                            ''')
    
                        result += ('<a class="%s" href="%s(3867, %i)">(%.1f) %s</a>, %s <br>\n'
                                   % (sec_class(sellsec), si, sellitem.stationID, sellsec, 
                                      cfg.evelocations.Get(sellitem.stationID).name, 
                                      cfg.evelocations.Get(sellitem.regionID).name))
                                        
                        result += ('<a class="%s" href="%s(3867, %i)">(%.1f) %s</a>, %s <br>\n'
                                   % (sec_class(buysec), si, buyitem.stationID, buysec,
                                      cfg.evelocations.Get(buyitem.stationID).name,
                                      cfg.evelocations.Get(buyitem.regionID).name))

                        result += ('<span>%i (%i from current location, %i seller -> buyer) %s</span> <br>\n'
                                   % (totaljumps, jumpsfromcurrent, jumpsfromsell, lowsecwarning)  )
                        result += '<div class="stats">\n'
                        result += ('<span>%i (%i -> %i)</span> <br>\n'
                                   % (tradable, sellitem.volRemaining, buyitem.volRemaining))
                        result += ('<span>%i (%.2f m&#179; each)</span> <br>\n'
                                   % (movable, item.volume))
                        result += ('<span>%s</span> <br>\n'
                                   % isk_string(sellitem.price))
                        result += ('<span>%s</span> <br>\n'
                                   % isk_string(buyitem.price))
                        result += ('<span>%s</span> <br>\n'
                                   % isk_string(investment))
                        result += ('<span>%s</span> <br>\n'
                                   % isk_string(tax))
                        result += ('<span class="total">%s</span> <br>\n'
                                   % isk_string(jumpprofit))
                        result += ('<span class="total">%s</span> <br>\n'
                                   % isk_string(tripprofit))
                        result += ('<span class="total">%s</span> <br>\n'
                                   % isk_string(profit))
                        result += '</div> <br>\n'

                        results.append([tripprofit, profit, jumpprofit, result])

    # add (sorted) results to output
    if len(results) == 0:
        output += 'No trades found.\n'
    else:
        output += ''.join(r[len(SORTSTRINGS)] for r in sorted(results, key=lambda x: x[sortby], reverse=True))

    output += ('</body>\n'
               '</html>')

    return output

# build typeid dictionary from cache data
typeids = {}
for invtype in cfg.invtypes:
    if invtype.marketGroupID in data.hastypes:
        if invtype.marketGroupID in typeids:
            typeids[invtype.marketGroupID].append(invtype.typeID)
        else:
            typeids[invtype.marketGroupID] = [invtype.typeID]

# header javascript for market scanner
scannerscript = '''
<script src="http://code.jquery.com/jquery.min.js"></script>
<script>
    typeids = %s
    selected = []
    timers = []
    active = false
    proglength = 150
    millis = 3000
    n = 1

    function loopDots() {
        s = $("#scan").text()
        if (s.length < 11)
            s += "."
        else
            s = "Scanning"
        $("#scan").text(s)
    }

    function nextItem(i, typeid) {
        barlength = proglength / n * (i + 1)
        $("#bar").css("width", barlength)
        $("#counter").text((i + 1) + " of " + n + " scanned")
        CCPEVE.showMarketDetails(typeid)
    }

    function toggleMarketScan() {
        if (!active && selected.length > 0) {
            active = true
            timers[0] = setInterval("loopDots()", millis/4)
            n = selected.length
            for (i = 0; i < n; i++) {
                timers[i+1] = setTimeout("nextItem("+i+", "+selected[i]+")", (i*millis)+10)
            }
            timers[n] = setTimeout("toggleMarketScan()", ((n-1)*millis)+10)
        } else {
            active = false
            $("#scan").text("Start market scan")
            clearInterval(timers[0])
            for (i = 1; i < timers.length; i++) {
                clearTimeout(timers[i])
            }
        }
    }

    function toggleGroup(g) {
        if ($("#c"+g).attr("checked")) {
            selected = selected.concat(typeids[g])
        } else {
            p = selected.indexOf(typeids[g][0])
            selected.splice(p, typeids[g].length)
        }
    }

    function toggleSet(box, set) {
        if ($(box).attr("checked")) {
            for (i = 0; i < set.length; i++) {
                $("#c"+set[i]).attr("checked", true)
                toggleGroup(set[i])
            }
        } else {
            for (i = 0; i < set.length; i++) {
                $("#c"+set[i]).attr("checked", false)
                toggleGroup(set[i])
            }
        }        
    }

    function toggleHeader(h) {
        $(h).siblings().toggle()
        s = $(h).text()
        if (s[s.length-1] == "-")
            s = s.replace("-", "+")
        else
            s = s.replace("+", "-")
        $(h).text(s)
    }
</script>
''' % str(typeids)

@route('/scan')
def scan():
    '''Automated market scanner page'''
    def traversegroups(group, headerlevel):
        '''Recursive traversal of groups, outputs headers and checkboxen'''
        string = ''
        checklist = []
        # sort empty subdictionaries first, these belong to current heading
        for key, members in sorted(group.items(), key=lambda x: len(x[1]) > 0):
            name = data.groupnames[key]
            if members:
                if checklist:
                    string += '<div class="checkchecker">'
                    string += '<input type="checkbox" onclick="toggleSet(this, %s)">All/none' % str(checklist)
                    string += '</div>\n'
                    checklist = []
                floater = ' class="floater"' if headerlevel == 2 else ''
                string += ('<div%s><h%i onclick="toggleHeader(this)">%s -</h%i>\n' 
                           % (floater, headerlevel, name, headerlevel))
                string += traversegroups(members, headerlevel+1)
                string += '</div>\n'
            else:
                if key in typeids.keys():
                    string += '<div class="checker">'
                    string += ('<input type="checkbox" name="%i" id="c%i" onclick="toggleGroup(%i)">%s' 
                               % (key, key, key, name))
                    string += '</div>\n'
                    checklist.append(key)
        if checklist:
            string += '<div class="checkchecker">'
            string += '<input type="checkbox" onclick="toggleSet(this, %s)">All/none' % str(checklist)
            string += '</div>\n'
        return string

    output = head % 'Automated market scanner' + scannerscript + headend
    output += textwrap.dedent('''
        <body>
        <div id="links">
        <a href="/">Trade finder</a>
        <span id="current">Automated market scanner</span>
        <a href="/orderwatch">Order watch</a>    
        </div>
        <h1>Automated market scanner</h1>
        <button id="scan" onclick="toggleMarketScan()">Start market scan</button>
        <div id="progress"> <span id="bar"></span> </div> <span id="counter"></span><br>
        <div>''')
    output += traversegroups(data.groupdict, 2)
    output += textwrap.dedent('''
        </div>
        </body>
        </html>''')

    return output

# header javascript for order watch
orderscript = '''
<script src="http://code.jquery.com/jquery.min.js"></script>
<script>
    scan = %s
    timers = []
    millis = 3000

    function refreshOrders() {
        scanner = ""
        if ($("#scancheck").attr("checked"))
            scanner = "?scanner=1"
        $("#ajaxorders").load("/getorders" + scanner);
    }

    function setScan(interval) {
        unsetScan()
        n = scan.length
        timers[0] = setInterval("refreshOrders(); toggleOrderScan()", (n*millis)+interval)
        for (i = 0; i < n; i++) {
            timers[i+1] = setTimeout("CCPEVE.showMarketDetails("+scan[i]+")", (i*millis)+interval)
        }
    }

    function unsetScan() {
        clearInterval(timers[0])
        for (i = 1; i < timers.length-1; i++) {
            clearTimeout(timers[i])
        }    
    }

    function toggleOrderScan() {
        if ($("#scancheck").attr("checked")) {
            setScan((5*60*1000))
        } else {
            unsetScan()
        }
    }
</script>
'''

orders = []

@route('/orderwatch')
def orderwatch():
    '''Order watch page'''
    global orders
    charid = int(request.headers.get('Eve-CharID') or 0)
    region = int(request.headers.get('Eve-RegionID') or 0)
    marketorders = auth.char.MarketOrders(charID=charid)
    orders = [order for order in marketorders.orders if order.orderState == 0]
    scan = [order.typeID for order in orders if data.stations[order.stationID] == region]

    output = head % 'Order watch' + orderscript % str(scan) + headend
    output += textwrap.dedent('''
        <body>
        <div id="links">
        <a href="/">Trade finder</a>
        <a href="/scan">Automated market scanner</a>
        <span id="current">Order watch</span>
        </div>
        <h1>Order watch</h1>
        <div id="ajaxorders">
        On first load, orders may be based on old data. Click <em>Scan and refresh</em> below.
        ''')
    output += getorders()
    output += textwrap.dedent('''
        </div>
        </body>
        </html>''')

    return output

@route('/getorders')
def getorders():
    '''Orders table'''
    sell, buy = index_market(24)

    outbid = []
    for order in orders:
        region = data.stations.get(order.stationID, 0)
        if order.bid:
            for hit in buy.get(order.typeID, []):
                if order.orderID == hit.orderID:
                    order.price = hit.price
                elif (region == hit.regionID and 
                    order.stationID == hit.stationID and 
                    order.price < hit.price):
                    outbid.append(order.typeID)
        else: 
            for hit in sell.get(order.typeID, []):
                if order.orderID == hit.orderID:
                    order.price = hit.price
                elif (region == hit.regionID and 
                    order.stationID == hit.stationID and 
                    order.price > hit.price):
                    outbid.append(order.typeID)
    outbid = list(set(outbid))

    output = textwrap.dedent('''
        <table>
        <tr>
        <th>Item</th>
        <th>Region</th>
        <th class="ralign">Price</th>
        <th class="ralign">Remaining</th>
        <th class="ralign">Entered</th>
        </tr>''')

    smd = 'javascript:CCPEVE.showMarketDetails'
    region = int(request.headers.get('Eve-RegionID') or 0)

    for order in sorted(orders, key=lambda x: x.price, reverse=True):
        mark = ' class="A"'
        warning = '<h2 class="X">Your order on <a class="J" href="%s(%i)">%s</a> has been outbid</h2>\n'
        if order.typeID in outbid:
            name = cfg.invtypes.Get(order.typeID).name
            output += warning % (smd, order.typeID, name)
            mark = ' class="X"'
        orderregion = data.stations.get(order.stationID, 0)
        if orderregion != region:
            mark = ''
        
        output += textwrap.dedent('''
            <tr>
            <td><a%s href="%s(%i)">%s</a></td>
            <td>%s</td>
            <td class="ralign">%s</td>
            <td class="ralign">%i</td>
            <td class="ralign">%i</td>
            </tr>''' % (mark, smd,
                        order.typeID,
                        cfg.invtypes.Get(order.typeID).name,
                        cfg.evelocations.Get(orderregion).name,
                        isk_string(order.price),
                        order.volRemaining, 
                        order.volEntered))

    scanner = int(request.query.scanner or 0)
    scanactive = ' checked="yes"' if scanner else ''
    output += textwrap.dedent('''
        </table>
        <button onclick="setScan(10)">Scan and refresh</button><br>
        <input type="checkbox" id="scancheck" onclick="toggleOrderScan()"%s>every 5 minutes
        ''' % scanactive)

    return output

if __name__ == '__main__':
    # run server
    run(host='localhost', port=80, reloader=True)
