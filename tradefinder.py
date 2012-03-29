# EVE Cache Trade Finder v0.7
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

EVEROOT = 'C:\Program Files (x86)\CCP\EVE'

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()
cachemgr = eve.getcachemgr()

# initial configuration
profitlimit = 1000000 # ISK
timelimit = 24        # hours
cargolimit = 1000     # m3
accounting = 0        # accounting skill level
sortby = 0            # selected sort option, see list below

SORTSTRINGS = ['Trip profit', 'Total profit', 'Profit per jump']
RESULTLIMIT = 200     # limit for total number of results

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
    '''General breadth first search'''
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

head = '''
<!doctype html>
<html>
<head>
<title>%s</title>
<style>
    body { background: #111; color: #ddd; font: 12px/18px Arial, sans-serif }
    h1 { font-size: 2em }
    h2 { font-size: 1.6em; color: #9f5 }
    h3 { font-size: 1.4em; color: #bd5 }
    h4 { font-size: 1.3em; color: #db5 }
    h5 { font-size: 1.2em; color: #f95 }
    h1, h2, h3, h4, h5 { line-height: 1em; margin: 0.5em 0 }
    h1 { background: #333; padding: 0.25em }
    h2.item { clear: both; margin: 0.5em 0; font-size: 1.2em }
    a, .item { color: #ccf; text-decoration: none }
    a:hover { text-decoration: underline }
    #links a { font-size: 1.25em; font-weight: bold }
    input, select, button { width: 115px; padding: 0 2px; background: #333; 
                            color: #fff; border: 1px solid #ddd; 
                            -webkit-box-sizing: border-box }
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

    cmc = cachemgr.LoadCacheFolder('CachedMethodCalls')

    # set user variables from url string
    profitlimit = int(request.query.profitlimit or profitlimit)
    timelimit = int(request.query.timelimit or timelimit)
    cargolimit = int(request.query.cargolimit or cargolimit)
    accounting = int(request.query.accounting or accounting)
    sortby = int(request.query.sortby or sortby)
    taxlevel = (1 - (accounting * 0.1)) * 0.01

    # index sell and buy data
    sell = {}
    buy = {}
    for key, obj in cmc.iteritems():
        if key[1] == 'GetOrders' and real_age(obj['used']) < timelimit:
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

    output = head % 'Trade finder' + headend
    # settings section
    output += textwrap.dedent('''
        <body>
        <div id="links">
        <a href="/scan">Automated market scanner &raquo;</a>
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
    if invtype['marketGroupID'] in data.hastypes:
        if invtype['marketGroupID'] in typeids:
            typeids[invtype['marketGroupID']].append(invtype['typeID'])
        else:
            typeids[invtype['marketGroupID']] = [invtype['typeID']]

# header javascript for market scanner
headscript = '''
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
                timers[i+1] = setTimeout("nextItem("+i+", "+selected[i]+")", i*millis)
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
            i = selected.indexOf(typeids[g][0])
            selected.splice(i, typeids[g].length)
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
        # sort empty subdictionaries first, these belong to current heading
        for key, members in sorted(group.items(), key=lambda x: len(x[1]) > 0):
            name = data.groupnames[key]
            if members:
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
        return string

    output = head % 'Automated market scanner' + headscript + headend
    output += textwrap.dedent('''
        <body>
        <div id="links">
        <a href="/">&laquo; Back to main screen</a>
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

def main():
    # run server
    run(host='localhost', port=80, reloader=True)

if __name__ == '__main__':
    main()
