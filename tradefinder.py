# EVE Cache Trade Finder v0.6
# Copyright (C) 2012 by Eirik Krogstad
# Licenced under the MIT License, see http://www.opensource.org/licenses/MIT
# Requires the Python libraries Bottle and Reverence
# Bottle: https://github.com/defnull/bottle
# Reverence: https://github.com/ntt/reverence

import time
from reverence import blue
from bottle import route, request, run
from collections import deque
import data

EVEROOT = 'C:\Program Files (x86)\CCP\EVE'

eve = blue.EVE(EVEROOT)
cfg = eve.getconfigmgr()
cachemgr = eve.getcachemgr()

# initial configuration
profitlimit = 1000000 # ISK
timelimit = 1         # hours
cargolimit = 1000     # m3
accounting = 0        # accounting skill level
sortby = 0            # selected sort option, see list below

SORTSTRINGS = ['Trip profit', 'Total profit', 'Profit per jump']
RESULTLIMIT = 100     # limit for total number of results

def real_age(t):
    '''Time since an EVE timestamp in hours'''
    return (time.time() - ((t - 116444736000000000) / 10000000)) / 3600

def isk_string(isk):
    '''Convert a number to a string on the form "1,000.00 ISK"'''
    return '{0:,.2f} ISK'.format(isk)

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
    paths = {None: []}
    for parent, child in breadth_first_search(graph, start):
        paths[child] = paths[parent] + [child]
        if child == end:
            return paths[child]
    return None

def path_length(graph, start, end):
    '''Get the length of the shortest path'''
    path = shortest_path(graph, start, end)
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
    a { color: #fa6; text-decoration: none }
    a:hover { text-decoration: underline }
    #links a { font-size: 1.25em; font-weight: bold }
    h1 { font-size: 2em }
    h2 { font-size: 1.6em; color: #9f5 }
    h3 { font-size: 1.4em; color: #bd5 }
    h4 { font-size: 1.3em; color: #db5 }
    h5 { font-size: 1.2em; color: #f95 }
    h1, h2, h3, h4, h5 { line-height: 1em; margin: 0.5em 0 }
    h1 { background: #333; padding: 0.25em }
    input, select, button { width: 115px; padding: 0 2px; background: #333; 
                            color: #fff; border: 1px solid #ddd; 
                            -webkit-box-sizing: border-box }
    .right, input[type="text"] { text-align: right }
    label, span.right { float: left; min-width: 120px }
    label, span.total { font-weight: bold }
    form label { margin: 3px 0 1px }
    select { padding: 0 }
    #scan { width: 150px; margin-right: 1em }
    #progress { border: 1px solid #ddd; height: 10px; width: 150px; top: 1px;
                display: inline-block; position: relative; margin-top: 0.5em }
    #bar { background: #666; height: 10px; width: 0; display: block;
           position: relative; overflow: hidden }
    input[type="checkbox"] { width: 15px }
    .floater { margin: 0 2em 2em 0; float: left; }
    .checker { min-width: 200px }
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
        if key[1] == 'GetOrders' and real_age(obj['runid']) < timelimit:
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
    output += '<body>\n'
    output += '<div id="links">\n'
    output += '<a href="/scan">Automated market scanner &raquo;</a>\n'
    output += '</div>\n'
    output += '<h1>Trade finder</h1>\n'
    if not request.headers.get('Eve-Trusted') == 'Yes':
        output += '<script>CCPEVE.requestTrust("http://localhost")</script>\n'
    output += '<form action="/" method="get">\n'
    output += '<label>Profit limit </label><input type="text" name="profitlimit" value="%i"> ISK<br>\n' % profitlimit
    output += '<label>Cache time limit </label><input type="text" name="timelimit" value="%i"> hours<br>\n' % timelimit
    output += '<label>Cargo limit </label><input type="text" name="cargolimit" value="%i"> m&#179;<br>\n' % cargolimit
    accountingoptions = ''
    for i in range(6):
        selected = ' selected="selected"' if accounting == i else ''
        accountingoptions += '<option value="%i"%s>%i</option>' % (i, selected, i)
    sortoptions = ''
    for i in range(len(SORTSTRINGS)):
        selected = ' selected="selected"' if sortby == i else ''
        sortoptions += '<option value="%i"%s>%s</option>' % (i, selected, SORTSTRINGS[i])
    output += '<label>Accounting skill </label><select name=accounting>%s</select> (tax level %.2f %%)<br>\n' % \
              (accountingoptions, taxlevel * 100)
    output += '<label>Sort by </label><select name=sortby>%s</select><br>\n' % (sortoptions)
    output += '<label>&nbsp;</label><input type="submit" value="Reload"><br>\n'
    output += '</form> <br>\n'

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
                    
                    if len(results) < RESULTLIMIT and \
                       (sortby == 0 and tripprofit > profitlimit) or \
                       (sortby == 1 and profit > profitlimit) or \
                       (sortby == 2 and tripprofit > profitlimit):
                        # add result to result list
                        smd = 'javascript:CCPEVE.showMarketDetails'
                        si = 'javascript:CCPEVE.showInfo'
                        result = '<strong><a href="%s(%i)">%s</a></strong> <br>\n' % (smd, typeid, item.name)
                        result += '<label>From:</label> <a href="%s(3867, %i)">%s</a>, %s <br>\n' % \
                                  (si, sellitem.stationID, 
                                   cfg.evelocations.Get(sellitem.stationID).name, 
                                   cfg.evelocations.Get(sellitem.regionID).name)                    
                        result += '<label>To:</label> <a href="%s(3867, %i)">%s</a>, %s <br>\n' % \
                                  (si, buyitem.stationID, 
                                   cfg.evelocations.Get(buyitem.stationID).name,
                                   cfg.evelocations.Get(buyitem.regionID).name)
                        fromcurrent = path_length(data.jumps, currentsystem, sellitem.solarSystemID)
                        fromsell = path_length(data.jumps, sellitem.solarSystemID, buyitem.solarSystemID)
                        totaljumps = fromcurrent + fromsell
                        jumpprofit = tripprofit / (totaljumps + 1)
                        result += '<label>Jumps:</label><span class="right">%i (%i from current location, %i seller -> buyer)</span> <br>\n' % \
                                  (totaljumps, fromcurrent, fromsell)  
                        result += '<label>Units tradable:</label><span class="right">%i (%i -> %i)</span> <br>\n' % \
                                  (tradable, sellitem.volRemaining, buyitem.volRemaining)
                        result += '<label>Units per trip:</label><span class="right">%i (%.2f m&#179; each)</span> <br>\n' % \
                                  (movable, item.volume)
                        result += '<label>Sell price:</label><span class="right">%s</span> <br>\n' % \
                                  isk_string(sellitem.price)
                        result += '<label>Buy price:</label><span class="right">%s</span> <br>\n' % \
                                  isk_string(buyitem.price)
                        result += '<label>Investment:</label><span class="right">%s</span> <br>\n' % \
                                  isk_string(investment)
                        result += '<label>Total tax:</label><span class="right">%s</span> <br>\n' % \
                                  isk_string(tax)
                        result += '<label>Profit per jump:</label><span class="right total">%s</span> <br>\n' % \
                                  isk_string(jumpprofit)
                        result += '<label>Profit per trip:</label><span class="right total">%s</span> <br>\n' % \
                                  isk_string(tripprofit)
                        result += '<label>Potential profit:</label><span class="right total">%s</span> <br>\n' % \
                                  isk_string(profit)
                        result += '<br>\n'
                        results.append([tripprofit, profit, jumpprofit, result])

    # add (sorted) results to output
    if len(results) == 0:
        output += 'No trades found.\n'
    else:
        for result in sorted(results, key=lambda x: x[sortby], reverse=True):
            output += result[3]

    output += '</body>\n'
    output += '</html>'

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
    millis = 3000
    proglength = $("#progress").css("width")

    function loopDots() {
        s = $("#scan").html()
        if (s.length < 11)
            s += "."
        else
            s = "Scanning"
        $("#scan").html(s)
    }

    function callMarket(i, typeid) {
        barlength = proglength / selected.length * (i + 1)
        $("#bar").css("width", barlength)
        CCPEVE.showMarketDetails(typeid)
    }

    function toggleMarketScan() {
        if (!active && selected.length > 0) {
            active = true
            timers[0] = setInterval("loopDots()", millis/4)
            for (i = 0; i < selected.length; i++) {
                timers[i+1] = setTimeout("callMarket("+i+", "+selected[i]+")", i*millis)
            }
            t = selected.length
            timers[t] = setTimeout("toggleMarketScan()", (t-1)*millis)
        } else {
            active = false
            $("#scan").html("Initialize market scan")
            clearInterval(timers[0])
            for (i = 1; i < timers.length; i++) {
                clearTimeout(timers[i])
            }
        }
    }

    function toggleGroup(n) {
        if ($("#c"+n).attr("checked")) {
            selected = selected.concat(typeids[n])
        } else {
            i = selected.indexOf(typeids[n][0])
            selected.splice(i, typeids[n].length)
        }
    }
</script>
''' % str(typeids)

@route('/scan')
def scan():
    '''Automated market scanner page'''

    def traversegroups(group, headerlevel):
        '''Recursive traversal of groups, outputs headers and checkboxen'''
        string = ''
        for key, members in group.iteritems():
            name = data.groupnames[key]
            if members:
                floater = ' class="floater"' if headerlevel == 2 else ''
                string += '<div%s><h%i>%s</h%i>\n' % \
                          (floater, headerlevel, name, headerlevel)
                string += traversegroups(members, headerlevel+1)
                string += '</div>'
            else:
                string += '<div class="checker"><input type="checkbox" name="%i" id="c%i" onclick="toggleGroup(%i)">%s</div>\n' % \
                          (key, key, key, name)
        return string

    output = head % 'Automated market scanner' + headscript + headend
    output += '<body>\n'
    output += '<div id="links">\n'
    output += '<a href="/">&laquo; Back to main screen</a>\n'
    output += '</div>\n'
    output += '<h1>Automated market scanner</h1>\n'
    output += '<button id="scan" onclick="toggleMarketScan()">Initialize market scan</button>'
    output += '<div id="progress"> <span id="bar"></span> </div> <br>\n'
    output += '<div>'
    output += traversegroups(data.groupdict, 2)
    output += '</div>'
    output += '</body>\n'
    output += '</html>'

    return output

# run server
run(host='localhost', port=80, reloader=True)
