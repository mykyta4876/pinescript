The Tradingview strategy uses two market trend indicators previously written by two other authors, one of them being a super trend using ATR and the second one being a super trend calculated by an N-Pole Gaussian filter (which involves machine learning). The strategy also uses a trailing stop loss of a dollar to exit the trades.

The trade entries are determined by the indicators: long entry when both indicators indicate an uptrend in the market and vice versa for shorts.

I developed the IBKR options trading bot with Tradingview and TWS API. For developing bot, I used Python TWS API framework. I deployed the webhook server in GCP vm instance.
I think my skils and experience are good fit with your project.
https://getdata-176241478587.us-central1.run.app
Message: {{strategy.order.comment}}


NVIDIA - 3 min time frame and the trailing stop loss is set to $0.10

the paper trading credentials are 
alczoi725/BillsBroker44!

https://afirmenetmx.com/webhook

sudo nano ~/dynu-credentials.ini
dns_dynu_auth_token = 65364264fb6442UYW37bfT3dZU66U44f

sudo certbot --authenticator dns-dynu --dns-dynu-credentials ~/dynu-credentials.ini certonly

=======================================
sudo apt update -y
sudo apt install python3 python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn requests pytz

mkdir ~/myflaskapp
sudo chmod 777 myflaskapp
cd ~/myflaskapp
sudo nano app.py
sudo chmod 777 app.py
sudo chmod 777 logger.py

Run the app with Gunicorn to test it:
sudo gunicorn -w 4 -b 0.0.0.0:80 app:app

http://34.41.120.34


sudo nano /etc/systemd/system/flaskapp.service
sudo systemctl daemon-reload
sudo systemctl start flaskapp
sudo systemctl enable flaskapp
sudo systemctl status flaskapp
sudo systemctl restart flaskapp

Let's start now.
=======================================
1. Deploy the app.py as a flask app in the GCP VM instance
	(1) create a vm instance in GCP
	 - click the button "Create Instance"
	 - set the name to 
	 - set a firewall rule to allow http and https traffic
	 - set the instance size to e2-micro
	 if you set e2-micro, you can save money.
	 - click the button "Create"
	 The instance created.
	(2) deploy the app.py file to the VM instance
	 - in terminal by using SSH, run:
		sudo apt update -y
		sudo apt install python3 python3-pip python3-venv -y
		mkdir ~/myflaskapp
		sudo chmod 777 myflaskapp
		cd ~/myflaskapp
		sudo nano app.py
		[copy the contents of app.py and paste it into the file
		after pasting, save and exit from nano by pressing CTRL+X, then press Y, then press Enter]
		sudo chmod 777 app.py
		sudo nano logger.py
		[copy the contents of logger.py and paste it into the file
		after pasting, save and exit from nano by pressing CTRL+X, then press Y, then press Enter]
		sudo chmod 777 logger.py
		python3 -m venv venv
		source venv/bin/activate
		pip install flask gunicorn requests pytz
		sudo nano /etc/systemd/system/flaskapp.service
		[replace "elonmusk710628" with your username in myflaskapp.service.txt and copy the contents of myflaskapp.service.txt and paste it into the file]
		sudo systemctl daemon-reload
		sudo systemctl start flaskapp
		sudo systemctl enable flaskapp

	 - you can check the status of the flask app with:
		sudo systemctl status flaskapp
		sudo journalctl -u flaskapp.service -xe
		[if you see "active (running)", it means the flask app is running.
		when open http://<VM_external_IP_address>/, it shows "Hello, World!"
		VM_external_IP_address = 34.30.24.141
		so when open http://34.30.24.141/, it shows "Hello, World!"
		]

	so far, you have deployed the flask app in the GCP VM instance.

2. Deploy the gcp_function.py as a cloud function
	(1) create a cloud function in GCP
		- navigate to the cloud function page in GCP
		- click the button "WRITE A FUNCTION"
		- set the name to "my-cloud-function"
		- set the runtime to python311
		- allow unauthenticated invocations
		- click the button "Create"
	(2) edit requirements.txt
		- add "requests" to the requirements.txt file
	(2) deploy the gcp_function.py file to the cloud function
		- replace vm_address with the external IP address of the VM instance in the gcp_function.py file
		- copy the contents of gcp_function.py and paste it into the cloud function
		- click the button "Save and Deploy"
		wait for a moment until the deployment is done.
	(3) test the cloud function
		you can test by browsing the url of the cloud function.
		https://my-cloud-function-176241478587.us-central1.run.app
	
	so far, you have deployed the cloud function.
3. Set alarm in tradingview to send message to the webhook
	(1) open your Pinescript strategy in Tradingview Pine Editor.
		- update the code with contents of "Supertrend Strategy.txt" and save it by pressing CTRL+S
		- click the button "Add to Chart" or "Update"
	(2) create a alarm
		- set the condition to "Supertend Strat" strategy.
		- set the message to {{strategy.order.comment}}
		- set webhook to public address of the GCP function.
	
	so far, you have set up the tradingview strategy and the cloud function.
4. Set up TWS settings.
		- you can refer https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#requests-limitations in order to set up the TWS settings.
		- download TWS from https://www.interactivebrokers.com/en/trading/tws-offline-latest.php
		- install TWS
		I already installed TWS in my computer.
		- TWS Configuration For API Use
			In TWS Global Configuration – API – Settings, there are many API settings. Please enable/disable some API settings based on your use case.
			In this section, only the most important API settings for API connection and incident troubleshooting are covered.
			Enable “ActiveX and Socket Clients”
			Disable “Read-Only API”
			Enable “Create API message log file”
			Enable “Include market data in API log file”
			Change “Logging Level” to “Detail”
		- Memory Allocation
			In TWS/ IB Gateway – “Global Configuration” – “General”, you can adjust the Memory Allocation (in MB)*.
			This feature is to control how much memory your computer can assign to the TWS/ IB Gateway application. Usually, higher value allows users to have faster data returning speed.
			Normally, it is recommended for API users to set 4000. However, it depends on your computer memory size because setting too high may cause High Memory Usage and application not responding.
		- Daily Reauthentication
			In TWS/ IB Gateway – “Global Configuration” – “Lock and Exit”, you can choose the time that your TWS will be shut down.
			For API users, it is recommended to choose “Never lock Trader Workstation” and “Auto restart”.
		- Order Precautions
			In TWS – “Global Configuration” – “API” – “Precautions”, you can enable the following items to stop receiving the order submission messages.

			Enable “Bypass Order Precautions for API orders”.
			Enable “Bypass Bond warning for API orders”.
			Enable “Bypass negative yield to worst confirmation for API orders”.
			Enable “Bypass Called Bond warning for API orders”.
			Enable “Bypass “same action pair trade” warning for API orders”.
			Enable “Bypass price-based volatility risk warning for API orders”.
			Enable “Bypass US Stocks market data in shares warning for API orders”.
			Enable “Bypass Redirect Order warning for Stock API orders”.
			Enable “Bypass No Overfill Protection precaution for destinations where implied natively”.
		- SMART Algorithm
			In TWS Global Configuration – Orders – Smart Routing, you can set your SMART order routing algorithm.
		- Download the TWS API
			download the TWS API from https://interactivebrokers.github.io/downloads/TWS%20API%20Install%201032.01.msi
		- install the TWS API
			I already installed the TWS API in my computer.
		- Updating The Python Interpreter
			Customers should then change their directory to  {TWS API}\source\pythonclient .
			It is then recommend to display the contents of the directory with “ls” for Unix, or “dir” for Windows users.
			Customers will now need to run the setup.py steps with the installation parameter. This can be done with the command: python setup.py install
			After running the prior command, users should see a large block of text describing various values being updated and added to their system. It is important to confirm that the version installed on your system mirrors the build version displayed. This example represents 10.25; however, you may have a different version.
			Finally, users should look to confirm their installation. The simplest way to do this is to confirm their version with pip. Typing this command should show the latest installed version on your system: python -m pip show ibapi

	so far, you have set up the TWS settings.
5. Run the client.py file
		- replace the ip address in the client.py file with the external IP address of the GCP VM instance
		VM_external_IP_address = 34.30.24.141
		- pip install flask, requests, pytz
		- run the client.py file in cmd
			python client.py

	so far, you have run the client.py file.

