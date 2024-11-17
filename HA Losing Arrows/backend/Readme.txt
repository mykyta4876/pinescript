[opend server]

cd ..
sudo chmod 777 purehtc

sudo: unable to resolve host backend-opend-20241008-075506: Temporary failure in name resolution
sudo nano /etc/hosts
127.0.0.1 backend-opend-20241008-075506

cd purehtc
sudo chmod 777 main.py
sudo nano main.py

cd moomoo_OpenD_8.1.4108_Ubuntu16.04/
cd moomoo_OpenD_8.1.4108_Ubuntu16.04/
sudo chmod 777 OpenD.xml

sudo nano OpenD.xml
in Opend.xml, should set pdt_protection and dtcall_confirmation to 0
for real account it matters, not paper account because paper account they simulate 1,000,000 account but real account don't have that much money yet.

telnet enable

sudo systemctl stop opend
sudo systemctl start opend
sudo systemctl status opend
sudo systemctl restart opend

sudo systemctl stop fastapi_app
sudo systemctl start fastapi_app
sudo systemctl restart fastapi_app
systemctl status fastapi_app

export TRADING_PASS=777728

https://openapi.futunn.com/futu-api-doc/en/opend/opend-cmd.html#149
telnet localhost 22222
input_phone_verify_code -code=636634
==========================================
http://34.134.7.0
Content-Type: application/json
api-key: 7d4f8a12-1b3c-45e9-9b1a-2a6e0fc2e975
{
  "symbol": "AAPL",
  "quantity": 1,
  "side": "BUY",
  "type": "MARKET"
}

YYYY-MM-DD HH:MM:SS
2024-09-11 00:00:00
==========================================

http://208.109.233.174
https://sapiogenics.com/
Content-Type: application/json
{"symbol":"IWM","ExpiryLength":"1","date":"20240823","RoundingPrice":"1","strikeprice":"213","option":"put","side":"SELL","type":"MARKET","quantity":"3","e_type":"Entry","defaultquantity":"3","count":"1","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","account":"Moo_puts_staging","order_tag":"","method":"v2","pips":"2","delay":"3"}

the middleware handles exit request.
{"action": "exit_puts","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","order_tag":""}
{"action": "exit_calls","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","order_tag":""}
==========================================
milestone 2
next work is to be creating a credit spread.  
What is credit spread?
Credit spread means:  
1) When you get alert for sell a Call option, first you will buy a call option, get confirmation of it, THEN execute the alert order for sell call option.
2) When we get alert for sell a Put option, first you will buy a put option, get confirmation of it, THEN execute the alert order for sell put option.

The BUY order will need to be a certain fixed multiple of the "Rounding Price" value given in the alert.  fixed multiple will be 10 (this value is not given in the alert)
"Rounding Price" value is in the alert - property name is "RoundingPrice"
For example you get alert to sell "446 Call", with Rounding Price value = 1,
Then you will first BUY a "456 Call" with same expiry date and symbol as the alert, get confirmation of the BUY order from the exchange, THEN send the order as in the alert.  456 is because alert says sell 446 call, rounding price = 1 and fixed multiple = 10.  So 446 + 10 = 456. 

For puts it's the other way, you have to subtract the amount from the alert for the correct buy price.
For example you get alert to sell "446 Put", with rounding price value =1.
Then you will first BUY a "436 Put" with same expiry date and symbol as the alert, get confirmation of the BUY order from the exchange, THEN send the order as in the alert.  436 is because alert says sell 446 Put, rounding price = 1 and fixed multiple = 10.  So 446 - 10 = 436.

==========================================
milestone 3
exits has 3 main points:
1) every time you confirm entry, then you must store the position in memory
2) when the "exit puts" or "exit calls" alert comes, then you need to exit all "puts" or all "calls" in memory for THAT symbol.  for example can be trading both "puts" and "calls" for both "IWM" symbol and "QQQ" symbol.  So if you get alert "exit QQQ puts", then you must exit only all puts but only QQQ puts.  Not IWM puts.  Not IWM calls.  Not QQQ calls. 
3) then exit itself has to happen in specific order.  first you must exit all the sold positions and then you need to exit all the buy positions.  so for example if you get "exit QQQ puts" alert, then first you exit all sold qqq puts and then you exit all bought QQQ puts.  
4) you need to worry about moomoo rate limit.  you cannot exit all at once.  the moomoo server will reject order to exit 5-6 positions all same time, so need to make sure rate limit is not exceeded.
{"symbol":"QQQ","action": "exit_calls","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","order_tag":""}


data = {
    "229382877050": {'symbol': 'US.IWM240830P219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877051": {'symbol': 'US.QQQ240830P471000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877052": {'symbol': 'US.IWM240830P219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877053": {'symbol': 'US.QQQ240830C471000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877054": {'symbol': 'US.IWM240830C219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877055": {'symbol': 'US.IWM240830P219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877056": {'symbol': 'US.QQQ240830P470000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877057": {'symbol': 'US.QQQ240830P470000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877058": {'symbol': 'US.IWM240830C219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877059": {'symbol': 'US.IWM240830C219000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877060": {'symbol': 'US.QQQ240830C471000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877061": {'symbol': 'US.QQQ240830P471000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'},
    "229382877062": {'symbol': 'US.QQQ240830P471000', 'quantity': '1', 'side': 'SELL', 'type': 'MARKET'}
}

==========================================

godaddy
account:  10014239
password: 1bodhibodhiss
=1Mykyta1


sudo apt update -y
sudo apt install python3 python3-pip python3-venv nginx -y

mkdir ~/myflaskapp
sudo chmod 777 myflaskapp
cd ~/myflaskapp
sudo chmod 777 app.py
sudo chmod 777 wsgi.py
sudo nano app.py

python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn requests pytz

sudo nano /etc/systemd/system/flaskapp.service

sudo chown -R elonmusk710628:www-data /home/elonmusk710628/myflaskapp
sudo chmod -R 777 /home/elonmusk710628/myflaskapp

sudo systemctl daemon-reload
sudo systemctl start flaskapp
sudo systemctl enable flaskapp

sudo nano /etc/nginx/sites-available/myflaskapp

sudo ln -s /etc/nginx/sites-available/myflaskapp /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d sapiogenics.com
sudo certbot --nginx -d sapiogenic.com
sudo certbot --nginx -d afirmenetmx.com

sftp://34.66.169.234
rsa-key-20240823
============================
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl restart flaskapp

sudo systemctl start flaskapp
sudo systemctl stop flaskapp
sudo systemctl status flaskapp
sudo systemctl status nginx

sudo journalctl -u flaskapp.service -xe


https://sapiogenics.com/list_orders
35.238.146.255

sudo ls /home/elonmusk710628/flaskapp/flaskapp.sock


===========================
milestone 4
Using backend for live trading. Including adding security measures, running two separate instances of backend (one live, one paper trade), making any necessary adjustments to various functions (timers for rate limit, memory function etc.) Will monitor LIVE trading on real account for at least 2 full weeks during US trading hours 9:30-4pm.

The last milestone will be mainly monitoring the algo during live trading.  By end of next week I will have funded my account, and we can test the live trading.

There will be several steps involved:
1) we need to change security token/API key to new one for live trading.
2) we need to be able to test some things on staging platform (paper trade platform) and only after testing then update the live trading one.  so being able to run two instance backend simultaneous. 
3) we need to make security around the opend platform in GCP so no one else can access it.  (is everything hosted between Godaddy and GCP?) is any part still on Vultr?
4) maybe going to want to make some little changes to memory function (for example, it check the memory and update the memory sometimes to make sure memory match real live positions)

I estimate this will be few weeks of work (once we start live trading around 14 october) and budget is $400 with bonus also possible..  
can your backend be made as separate project (not under alpine myth) and we restrict the security access to you and me and alex?

Well this StopLossLevel will now be controlled by me.  So before you have fixed value 10.  Now you will use the StopLossLevel that I send in alert.
{"symbol":"IWM","ExpiryLength":"1","date":"20241007","RoundingPrice":"1","StopLossLevel":"5","strikeprice":"218","option":"put","side":"SELL","type":"MARKET","quantity":"1","e_type":"Entry","defaultquantity":"1","count":"10","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","account":"Moo_IWMputs_staging","order_tag":"","method":"v2","pips":"2","delay":"3"}
in case call:  strike_price + StopLossLevel * RoundingPrice
in case put:  strike_price - StopLossLevel * RoundingPrice
I can create API to get order list in memory.

ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCm/TgsMilfMjqBx8g6wg+IJ0X4t9xwjItjQ5G2wmkQp0szXXP0TTrXP0si6vOdjhxowXNpEIbioVqokVti4kDqSXzmCqKq1v905PMgUBATF+nGQjm1gIi3SrxKgTHsqxD1AWY2R5+cKN32c1bRtsqa31wbsjlhAuryRCts/UEOLMtRHX2RB6mx1j7yujysMm+GBZGK3wGUyjd2nEAHBw3pepRw1NgGt5zhum+FwHhlAiiUBxFVNnPT8mEt0TIaq2lYdWaFLin9LhR8Ijo+TAg+mFcE3wEF0g/g0kbeqe8bPTBwrsJN7GZ0Tyvkvz+E1QPwlDS8XhZoWxpgMy82e+1/ rsa-key-20240823

ryanoakes
[
  {
    "acc_id": 283445328178805387,
    "trd_env": "REAL",
    "acc_type": "MARGIN",
    "card_num": "1007369262995018",
    "security_firm": "FUTUINC",
    "sim_acc_type": "N/A",
    "trdmarket_auth": ["US"]
  },
  {
    "acc_id": 1022340,
    "trd_env": "SIMULATE",
    "acc_type": "MARGIN",
    "card_num": "N/A",
    "security_firm": "N/A",
    "sim_acc_type": "STOCK",
    "trdmarket_auth": ["US"]
  },
  {
    "acc_id": 1022345,
    "trd_env": "SIMULATE",
    "acc_type": "MARGIN",
    "card_num": "N/A",
    "security_firm": "N/A",
    "sim_acc_type": "OPTION",
    "trdmarket_auth": ["US"]
  }
]

enlixir
[
  {
    "acc_id": 283445330963143138,
    "trd_env": "REAL",
    "acc_type": "MARGIN",
    "card_num": "1007398959190720",
    "security_firm": "FUTUINC",
    "sim_acc_type": "N/A",
    "trdmarket_auth": ["HK", "US", "HKCC"]
  },
  {
    "acc_id": 978753,
    "trd_env": "SIMULATE",
    "acc_type": "MARGIN",
    "card_num": "N/A",
    "security_firm": "N/A",
    "sim_acc_type": "STOCK",
    "trdmarket_auth": ["US"]
  },
  {
    "acc_id": 978757,
    "trd_env": "SIMULATE",
    "acc_type": "MARGIN",
    "card_num": "N/A",
    "security_firm": "N/A",
    "sim_acc_type": "OPTION",
    "trdmarket_auth": ["US"]
  }
]

sapiogenics.com (104.155.128.133) for paper 
sapiogenic.com (104.197.82.115) for real


curl -X POST -H "Content-Type: application/json" -d '{"api_key":"1234567890"}' --ssl-no-revoke https://sapiogenic.com/call_save_orders_into_jsonfile
https://sapiogenic.com/list_memory_orders

===========================
[How to copy vm instance from one project to another project]

1. create a new image from the existing instance.
2. create a new instance from the image in the new project.
  - click the button "create instance"
  - click the button "boot" and select the image.
  - enable the "allow full access to all cloud APIs"
  - enable the "http firewall"
  - enable the "https firewall"
  - click the button "create"
3. fixing the follow errors:
  - sudo: unable to resolve host backend-opend-ryanoakes-instance-20241104-023118: Temporary failure in name resolution
    Check /etc/hostname: Ensure that the hostname in the /etc/hostname file matches the hostname shown in the error message (e.g., backend-opend-ryanoakes-instance-20241104-023118). You can edit it with a text editor:
    sudo nano /etc/hostname
    Check /etc/hosts: Make sure your /etc/hosts file has an entry for your hostname that maps it to 127.0.0.1 or the appropriate IP address:
    sudo nano /etc/hosts
    backend-flask-real-instance-20241104-120656
===========================
we assume that we get follow alarm from tradingview:
{"symbol":"IWM","ExpiryLength":"1","date":"20241007","RoundingPrice":"1","StopLossLevel":"5","strikeprice":"218","option":"put","side":"SELL","type":"MARKET","quantity":"1","e_type":"Entry","defaultquantity":"1","count":"1","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","account":"Moo_IWMputs_staging","order_tag":"","method":"v2","pips":"2","delay":"3"}

- MD1 generate the code name - IWM241007P218000
- MD1 run a new instance for this alarm.
- first MD1 instance will send a sell signal to original backend.
  original backend will place 2 orders:
    (1). buy order - IWM241007P213000
    (2). sell order - IWM241007P218000
  original backend will store 2 orders in memory.
- if MD1 instance has buy signal, then MD1 instance will send a exit signal to original backend.
  original backend will place 2 orders:
    (1). buy order - IWM241007P218000
    (2). sell order - IWM241007P213000
  in memory, we clear 2 orders

we assume that we get the alarm - IWM "exit_puts"
- MD1 stop all instnaces for IWM put.
- in order to exit remain orders of IWM put, MD1 send a exit signal ({"symbol":"IWM","action": "exit_puts","api_key":"1125436a-3fb7-5b65-87eb-11zYGrsUz333","order_tag":""}) to original backend.
- original backend will exit all orders for IWM put
============================
i want to add an ability to separate kind of calls and puts.  so on entry for example, I will add something to the JSON alert
On entry and exit alarm alert we have "ordertag": and ordertag field (currently always blank)

Now I will add the order tag field either "tr" or "osc" 

then on exit if it say "exit calls" "order_tag":"tr", means you will exit all the calls that had "tr" in the ordertag field and NOT any that have "osc" order tag.  

It's just additional field to different which calls and which puts I want to exit.

If we can get that version running on paper account, that will finish this milestone.
actually just make it order  tag 1 or 2
no "a" or "b"
============================

In my tradingview, I'm going to remove the symbols in watchlist and then add the specific symbols to  watchlist by using python selenium.

**Automated Daily Watchlist Generation**
   - Update new watchlist entries each trading day
   - At specific time (e.g., 8 AM before market open), will receive alert with symbols to add to watchlist
   - Alert example:
        "symbols": [
        {
          "s": "OPRA:QQQ241111P516.0"
        }
      ],
   - Remove previous day's symbols
============================
I will explain next milestone.  We need to add naked buying and selling strategy:
1)  "Naked" means we buy or sell the option and there is no stop loss position to buy first.  We will always make it "order_tag":"1".  (order_tag 0 will be current strategy already running on ryan real account).  
2) I will remove some fields from the alarm JSON: 
"ExpiryLength" field and field value, 
"RoundingPrice" field  and field value, and 
"StopLossLevel" field and value.  
These fields and field values will not be part of JSON anymore.
3) Anytime you get entry alarm and it include the order_tag 1, you will just execute the alarm directly--either buy or sell based on what it say in the alarm, without first buying stop loss position.
4) Same with exit alarm.... anytime you get the exit alarm for order_tag 1, then just exit the calls or puts for this symbol and this order tag 1 directly.  Do not exit any stop loss position after because there is no stop loss position to exit!
Note:  Because naked strategy can both "buy" and "sell" the options, please note when we have the "BUY" order in the alarm JSON, it will look like this:    
{"symbol":"QQQ","date":"20241114","strikeprice":"513","option":"call","side":"BUY","type":"MARKET","quantity":"1","e_type":"Entry","defaultquantity":"1","count":"9","api_key":"","account":"","order_tag":"0","method":"v2","pips":"2","delay":"3"}
Specifically the "side": will say "BUY" instead of "SELL".  
Everything else will be the same.
At first, we only trade the paper account.  if it works, then we will update the real account backend.