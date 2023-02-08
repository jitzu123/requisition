from flask import Flask, request, render_template, g, url_for, session, jsonify, redirect
import sqlite3 as sqlite
from datetime import date
from werkzeug.utils import secure_filename
import os
from twilio.rest import Client
import datetime
import json
import smtplib
from flask_mail import Mail, Message
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from email.mime.base import MIMEBase 
from email import encoders
import random
import string

mail = Mail()
currentDate = datetime.datetime.now()

client = Client("AC723cbd4d958b5bc60a6e9daf709790a3","621d65c39e312ab443279a864dea98f1")

app = Flask(__name__)
app.secret_key = '/dww213sdd2!@1'
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def conn():
    g.conn = sqlite.connect("inventory.db")
    g.cur = g.conn.cursor()

@app.route("/")
def index():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	pending_petty_cash = getPendingRequestsCount('petty_cash', data[8], data[9])
	pending_purchase_request = getPendingRequestsCount('purchase_request', data[8], data[9])

	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/index.html",data=data, pending_petty_cash=pending_petty_cash, pending_purchase_request=pending_purchase_request)
	elif data[8] == "CASHIER":
		approved_purchase_request = getPendingRequestsCount("petty_cash", "APPROVED", "")
		return render_template("cashier/index.html",data=data,approved_purchase_request=approved_purchase_request)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/index.html",data=data, pending_petty_cash=pending_petty_cash, pending_purchase_request=pending_purchase_request)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/index.html",data=data, pending_petty_cash=pending_petty_cash, pending_purchase_request=pending_purchase_request)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/index.html",data=data, pending_petty_cash=pending_petty_cash, pending_purchase_request=pending_purchase_request)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/index.html",data=data, pending_purchase_request=pending_purchase_request)
	elif data[8] == "FACULTY":
		pending_petty_cash = getOwnRequestsCount('petty_cash', "PENDING", data[0])
		approve_petty_cash = getOwnRequestsCount('petty_cash', "APPROVED", data[0])
		disapprove_petty_cash = getOwnRequestsCount('petty_cash', "DISAPPROVED", data[0])

		pending_purchase_request = getOwnRequestsCount('purchase_request', "PENDING", data[0])
		approve_purchase_request = getOwnRequestsCount('purchase_request', "APPROVED", data[0])
		disapprove_purchase_request = getOwnRequestsCount('purchase_request', "DISAPPROVED", data[0])
		return render_template("employee/index.html",data=data, 
								pending_petty_cash=pending_petty_cash, approve_petty_cash=approve_petty_cash, disapprove_petty_cash=disapprove_petty_cash, 
								pending_purchase_request=pending_purchase_request,approve_purchase_request=approve_purchase_request, disapprove_purchase_request=disapprove_purchase_request)
	elif data[8] == "PMO":
		approved_purchase_request = getPendingRequestsCount("purchase_request", "APPROVED", "")
		return render_template("pmo/index.html",data=data,approved_purchase_request=approved_purchase_request)
	else:
		sql = '''SELECT 
					(SELECT count(id) FROM `accounts`) AS `users`,
					(SELECT COUNT(id) FROM `petty_cash` WHERE `Status` = 'APPROVED') AS `approved_petty_cash`,
					(SELECT COUNT(id) FROM `petty_cash` WHERE `Status` = 'DISAPPROVED') AS `disapproved_petty_cash`,
					(SELECT COUNT(id) FROM `purchase_request` WHERE `Status` = 'APPROVED') AS `approved_purchase_request`,
					(SELECT COUNT(id) FROM `purchase_request` WHERE `Status` = 'DISAPPROVED') AS `disapproved_purchase_request` '''
		g.cur.execute(sql)
		dashboard = g.cur.fetchall()

		return render_template("index.html",data=data,dashboard=dashboard)

@app.route("/login")
def login():
	if 'log' in session:
		return redirect(url_for("routing"))
	return render_template("login.html")

@app.route("/login_process",methods=['POST'])
def login_process():
	username = request.form['username']
	password = request.form['password']

	sql = "SELECT * FROM accounts JOIN department_office ON accounts.department = department_office.id WHERE username='{}' AND password='{}' and accounts.status = 'Active'".format(username,password)
	g.cur.execute(sql)
	data = g.cur.fetchall()

	if len(data) > 0:
		session['log'] = data[0]

	return redirect(url_for("routing"))

@app.route("/register")
def register():
	if 'log' in session:
		return redirect(url_for("routing"))
	sql = "SELECT * FROM department_office WHERE status = 'Active'"
	g.cur.execute(sql)
	department = g.cur.fetchall()
	
	return render_template("register.html", department=department)

@app.route("/forgot_password")
def forgot_password():
	if 'log' in session:
		return redirect(url_for("routing"))
	return render_template("forgot_password.html")

@app.route("/forgot_process",methods=['POST'])
def forgot_process():
	email = request.form['email']
	
	sql = "SELECT id FROM accounts WHERE email = '{}'".format(email)
	g.cur.execute(sql)
	user = g.cur.fetchall()

	sql = "UPDATE accounts SET status = 'Forgot Password' WHERE id = '{}'".format(user[0][0])
	g.cur.execute(sql)
	g.conn.commit()
	return "success"

@app.route("/register_process",methods=['POST'])
def register_process():
	fname = request.form['fname'].title()
	lname = request.form['lname'].title()
	contact = request.form['contact']
	account = request.form['account']
	address = request.form['address']
	email = request.form['email']
	username = request.form['username']
	password = request.form['password']
	department = request.form['department']
	
	sql = "INSERT INTO accounts(fname,lname,username,password,contact,email,address,account,department,status) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}','Verify')".format(fname,lname,username,password,contact,email,address,account,department)
	g.cur.execute(sql)
	g.conn.commit()
	return "success"

@app.route("/logout")
def logout():
	session.pop("log",None)
	return redirect(url_for("login"))

@app.route("/routing")
def routing():
	if 'log' in session:
		return redirect(url_for('index'))
	return redirect(url_for("login"))

@app.route("/profile")
def profile():
	if "log" not in session:
		return redirect(url_for("login"))
	info = session['log']

	sql = "SELECT * FROM accounts WHERE accounts.id = '{}'".format(info[0])
	g.cur.execute(sql)
	user = g.cur.fetchall()
	
	if session['log'][8] == 'DEAN' or session['log'][8] == 'DEPARTMENT HEAD' or session['log'][8] == 'OFFICE HEAD':
		return render_template("head/profile.html",data=info,user=user)
	elif session['log'][8] == 'BUDGET CLERK':
		return render_template("bc/profile.html",data=info,user=user)
	elif session['log'][8] == 'FINANCE HEAD':
		return render_template("fh/profile.html",data=info,user=user)
	elif session['log'][8] == "SCHOOL PRESIDENT":
		return render_template("sp/profile.html",data=info,user=user)
	elif session['log'][8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/profile.html",data=info,user=user)
	elif session['log'][8] == "PMO":
		return render_template("pmo/profile.html",data=info,user=user)
	elif session['log'][8] == "CASHIER":
		return render_template("cashier/profile.html",data=info,user=user)
	else:
		return render_template("employee/profile.html",data=info,user=user)

@app.route('/edit_profile',methods=['POST'])
def edit_profile():
	_id = session['log'][0]
	fname = request.form['fname'].title()
	lname = request.form['lname'].title()
	email = request.form['email']
	contact = request.form['contact']
	address = request.form['address']

	sql = "UPDATE accounts SET fname = '{}', lname = '{}', email = '{}', contact = '{}', address = '{}' WHERE id = '{}'".format(fname, lname, email, contact, address, _id)
	g.cur.execute(sql)
	g.conn.commit()

	return redirect(url_for("profile"))

# --------------------------------------------- EMPLOYEE -------------------------------------------- #

@app.route("/change_password", methods=['POST'])
def change_password():
	_id = session['log'][0]
	old_password = request.form['old_password']
	new_password = request.form['new_password']

	sql = "SELECT * FROM accounts WHERE password='{}'".format(old_password)
	g.cur.execute(sql)
	data = g.cur.fetchall()

	if len(data) == 1:
		print('hi')
		sql = "UPDATE accounts SET password='{}' WHERE id='{}'".format(new_password,_id)
		g.cur.execute(sql)
		g.conn.commit()

		return redirect(url_for("routing"))
	else:
		return "Invalid Old Password"

# ---- PURCHASE REQUEST
@app.route("/purchase_request_form")
def purchase_request_form():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/purchase_request_form.html",data=data)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/purchase_request_form.html",data=data)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/purchase_request_form.html",data=data)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/purchase_request_form.html",data=data)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/purchase_request_form.html",data=data)
	elif data[8] == "PMO":
		return render_template("pmo/purchase_request_form.html",data=data)
	elif data[8] == "CASHIER":
		return render_template("cashier/purchase_request_form.html",data=data)
	else:
		return render_template("employee/purchase_request_form.html",data=data)

@app.route("/submit_purchase_request/<int:user_id>",methods=['POST'])
def submit_purchase_request(user_id):
	employee = request.form['employee']
	date = request.form['date']
	purpose = request.form['purpose']
	office = request.form['office']
	item_number = request.form.getlist('item_number[]')
	quantity = request.form.getlist('quantity[]')
	unit_of_issue = request.form.getlist('unit_of_issue[]')
	item_description = request.form.getlist('item_description[]')
	estimated_unit_cost = request.form.getlist('estimated_unit_cost[]')
	estimated_amount = request.form.getlist('estimated_amount[]')

	charge_to_account = request.form['charge_to_account']
	budget_allocation = request.form['budget_allocation']
	date_of_utilization = request.form['date_of_utilization']
	account_code = request.form['account_code']
	budget_remaining = request.form['budget_remaining']
	request_type = request.form['request_type']

	if request.files.get('file', None):
		image = request.files['file']
		print(image)
		image_filename = secure_filename(image.filename)
		image.save(os.path.join(UPLOAD_FOLDER, image_filename))
	else:
		image_filename = None

	total_estimated_unit_cost = 0
	total_estimated_amount = 0
	year = currentDate.year

	if session['log'][8] == 'FACULTY':
		sql = "INSERT INTO purchase_request(charge_to_account, budget_allocation, date_of_utilization, account_code, budget_remaining, employee, date, purpose, office, user_id, pr_type, file_path) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(charge_to_account, budget_allocation, date_of_utilization, account_code, budget_remaining, employee,date,purpose,office,user_id,request_type,image_filename)
	else:
		sql = "INSERT INTO purchase_request(charge_to_account, budget_allocation, date_of_utilization, account_code, budget_remaining, employee, date, purpose, office, user_id, pr_type, status, file_path) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','BUDGET CLERK','{}')".format(charge_to_account, budget_allocation, date_of_utilization, account_code, budget_remaining, employee,date,purpose,office,user_id,request_type,image_filename)

	g.cur.execute(sql)
	g.conn.commit()

	_id = g.cur.lastrowid
	form_id = "{}-{}".format(year,_id)

	for i in range(len(item_number)):
		sql = "INSERT INTO items(form_id,item_number,quantity,unit_of_issue,item_description,estimated_unit_cost,estimated_amount) VALUES('{}','{}','{}','{}','{}','{}','{}')".format(_id,item_number[i],quantity[i],unit_of_issue[i],item_description[i],estimated_unit_cost[i],estimated_amount[i])
		total_estimated_unit_cost = total_estimated_unit_cost+float(estimated_unit_cost[i])
		total_estimated_amount = total_estimated_amount+float(estimated_amount[i])
		g.cur.execute(sql)
		g.conn.commit()

	sql = "UPDATE purchase_request SET form_id='{}', estimated_amount='{}', estimated_unit_cost='{}' WHERE id='{}'".format(form_id,total_estimated_amount,total_estimated_unit_cost,_id)
	g.cur.execute(sql)
	g.conn.commit()

	_message = "NEW PENDING PURCHASE REQUEST from {}".format(employee)
	# sendGroupMessage(_message,"BUDGET CLERK")
	sendGroupEmail(_message,"OFFICE HEAD")
	sendGroupEmail(_message,"DEPARTMENT HEAD")
	sendGroupEmail(_message,"DEAN")

	if session['log'][8] == 'FACULTY':
		return jsonify({'data': 'success', 'route': 'view_purchase_request_forms'})
	else:
		return jsonify({'data': 'success', 'route': 'my_forms'})

@app.route("/cancel_purchase_request_form/<int:id>")
def cancel_purchase_request_form(id):
	sql = "UPDATE purchase_request SET status='CANCELLED' WHERE id='{}'".format(id)
	g.cur.execute(sql)
	g.conn.commit()
	return redirect(url_for("view_purchase_request_forms"))

@app.route("/view_purchase_request_form/<int:id>")
def view_purchase_request_form(id):
	data = session['log']
	purchase = getPurchaseRequestFormData(id)

	sql = "SELECT * FROM items WHERE form_id='{}'".format(purchase[0])
	g.cur.execute(sql)
	items = g.cur.fetchall()
	
	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/view_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/view_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/view_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/view_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/view_purchase_request_form.html",data=data,purchase=purchase,items=items)
	else:
		return render_template("employee/view_purchase_request_form.html",data=data,purchase=purchase,items=items)

@app.route("/view_purchase_request_forms")
def view_purchase_request_forms():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	forms = getPurchaseRequestForms(data[8])
	
	return render_template("employee/display_purchase_request_forms.html",data=data,forms=forms)

# ---- PETTY CASH
@app.route("/cancel_petty_cash_form/<int:id>")
def cancel_petty_cash_form(id):
	sql = "UPDATE petty_cash SET status='CANCELLED' WHERE id='{}'".format(id)
	g.cur.execute(sql)
	g.conn.commit()
	return redirect(url_for("view_petty_cash_forms"))

@app.route("/petty_cash_form")
def petty_cash_form():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	
	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/petty_cash_form.html",data=data)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/petty_cash_form.html",data=data)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/petty_cash_form.html",data=data)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/petty_cash_form.html",data=data)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/petty_cash_form.html",data=data)
	elif data[8] == "PMO":
		return render_template("pmo/petty_cash_form.html",data=data)
	elif data[8] == "CASHIER":
		return render_template("cashier/petty_cash_form.html",data=data)
	else:
		return render_template("employee/petty_cash_form.html",data=data)

@app.route("/submit_petty_cash/<int:user_id>", methods=['POST'])
def submit_petty_cash(user_id):
	employee = request.form['employee']
	date = request.form['date']
	department_office = request.form['department_office']
	budget_code = request.form['budget_code']
	amount_in_words = request.form['amount_in_words']
	php = request.form['php']
	purpose = request.form['purpose']
	if request.files.get('file', None):
		image = request.files['file']
		image_filename = secure_filename(image.filename)
		image.save(os.path.join(UPLOAD_FOLDER, image_filename))
	else:
		image_filename = None

	if session['log'][8] == 'FACULTY':
		sql = "INSERT INTO petty_cash(user_id,department_office,budget_code,date,amount_in_words,php,purpose,employee,file_path) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(user_id,department_office,budget_code,date,amount_in_words,php,purpose,employee,image_filename)
	else:
		sql = "INSERT INTO petty_cash(user_id,department_office,budget_code,date,amount_in_words,php,purpose,employee,status,file_path) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','BUDGET CLERK','{}')".format(user_id,department_office,budget_code,date,amount_in_words,php,purpose,employee,image_filename)

	g.cur.execute(sql)
	g.conn.commit()
	_id = g.cur.lastrowid

	year = currentDate.year
	pc_number = "{}-{}".format(year,_id)

	sql = "UPDATE petty_cash SET pc_number='{}' WHERE id='{}'".format(pc_number,_id)
	g.cur.execute(sql)
	g.conn.commit()

	_message = "NEW PENDING PETTY CASH REQUEST from {}".format(employee)
	sendGroupEmail(_message,"OFFICE HEAD")
	sendGroupEmail(_message,"DEPARTMENT HEAD")
	sendGroupEmail(_message,"DEAN")
	if session['log'][8] == 'FACULTY':
		# return redirect(url_for("view_petty_cash_forms"))
		return jsonify({'data': 'success', 'route': 'view_petty_cash_forms'})
	else:
		# return redirect(url_for("my_forms"))
		return jsonify({'data': 'success', 'route': 'my_forms'})

@app.route("/view_petty_cash_form/<int:id>")
def view_petty_cash_form(id):
	data = session['log']
	info = getPettyCashFormData(id)

	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/view_petty_cash_form.html",data=data,info=info)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/view_petty_cash_form.html",data=data, info=info)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/view_petty_cash_form.html",data=data, info=info)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/view_petty_cash_form.html",data=data, info=info)
	elif data[8] == "CASHIER":
		return render_template("cashier/view_petty_cash_form.html",data=data, info=info)
	else:
		return render_template("employee/view_petty_cash_form.html",data=data,info=info)

@app.route("/view_petty_cash_forms")
def view_petty_cash_forms():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	forms = getPettyCashForms(data[8])
	
	return render_template("employee/display_petty_cash_forms.html",data=data,forms=forms)

@app.route("/incoming")
def incoming():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	petty_cash = getPettyCashForms(data[8])
	purchase_request = getPurchaseRequestForms(data[8])

	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/incoming.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/incoming.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/incoming.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/incoming.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/incoming.html",data=data, purchase_request=purchase_request)
	elif data[8] == "PMO":
		return render_template("pmo/incoming.html",data=data, purchase_request=purchase_request)
	elif data[8] == "CASHIER":
		return render_template("cashier/incoming.html",data=data, petty_cash=petty_cash)

@app.route("/outgoing")
def outgoing():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']

	petty_cash = getPettyCashOutgoingForms(data[8])
	purchase_request = getPurchaseRequestOutgoingForms(data[8])

	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/outgoing.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/outgoing.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "SCHOOL ACCOUNTANT":
		return render_template("sa/outgoing.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/outgoing.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/outgoing.html",data=data, purchase_request=purchase_request)

# --------------------------------------------- END EMPLOYEE -------------------------------------------- #

# --------------------------------------------- HEAD -------------------------------------------- #

@app.route("/head_approve_petty_cash_form/<int:id>")
def head_approve_petty_cash_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']

	sql = "UPDATE petty_cash SET head_of_office_department='{} {}', status='BUDGET CLERK', head_sig='{}' WHERE id='{}'".format(data[1],data[2],data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM petty_cash WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]
	
	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Petty Cash Approved by {} {} Pending for Budget Clerk".format(data[1],data[2])
	send_email(_message,email)

	_message = "New Petty Cash waiting for Budget Clerk Approval"
	sendGroupEmail(_message,"BUDGET CLERK")
	return jsonify({'data': 'success', 'route': 'incoming'})

@app.route("/head_approve_purchase_request_form/<int:id>")
def head_approve_purchase_request_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	today = currentDate.strftime("%m/%d/%Y")

	sql = "UPDATE purchase_request SET status='BUDGET CLERK', head_of_office_department='{} {}', head_of_office_department_date='{}', head_sig='{}' WHERE id='{}'".format(data[1],data[2],today,data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM purchase_request WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Purchase Request Approved by {} {} Pending for Budget Clerk".format(data[1],data[2])
	send_email(_message, email)
	# sendMessage(_message,_id)

	_message = "New Purchase Request waiting for Budget Clerk Approval"
	# sendGroupMessage(_message,"BUDGET CLERK")
	sendGroupEmail(_message,"BUDGET CLERK")
	return jsonify({'data': 'success', 'route': 'incoming'})

@app.route("/dissaprove/<int:id>/<form_type>", methods=['POST'])
def dissaprove(id, form_type):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	remarks = request.form['inputValue']
	
	sql = "SELECT user_id FROM {} WHERE id='{}'".format(form_type, id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]
	
	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	if form_type == 'petty_cash':
		_message = "Petty Cash Disapproved by {} {} with the following reason: {}".format(data[1],data[2], remarks)
	else:
		_message = "Purchase Request Disapproved by {} {} with the following reason: {}".format(data[1],data[2], remarks)
	
	sql = "UPDATE {} SET status='DISAPPROVED', remarks='{}' WHERE id='{}'".format(form_type, _message, id)
	g.cur.execute(sql)
	g.conn.commit()

	send_email(_message,email)
	return jsonify({'data': 'success', 'route': 'incoming'})

@app.route("/my_forms")
def my_forms():
	if "log" not in session:
		return redirect(url_for("login"))	
	data = session['log']
	
	petty_cash = getMyForms(session['log'][0], 'Petty Cash')
	purchase_request = getMyForms(session['log'][0], 'Purchase Request')
	
	if data[8] == 'OFFICE HEAD' or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'BUDGET CLERK':
		return render_template("bc/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'SCHOOL ACCOUNTANT':
		return render_template("sa/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'FINANCE HEAD':
		return render_template("fh/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'SCHOOL PRESIDENT':
		return render_template("sp/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'PMO':
		return render_template("pmo/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)
	elif data[8] == 'CASHIER':
		return render_template("cashier/my_forms.html",data=data, petty_cash=petty_cash, purchase_request=purchase_request)

@app.route("/own_petty_cash_form/<int:id>")
def own_petty_cash_form(id):
	data = session['log']
	info = getPettyCashFormData(id)

	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/own_petty_cash_form.html",data=data,info=info)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/own_petty_cash_form.html",data=data, info=info)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/own_petty_cash_form.html",data=data, info=info)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/own_petty_cash_form.html",data=data, info=info)
	elif data[8] == "PMO":
		return render_template("pmo/own_petty_cash_form.html",data=data, info=info)
	else:
		return render_template("employee/view_petty_cash_form.html",data=data,info=info)

@app.route("/own_purchase_request_form/<int:id>")
def own_purchase_request_form(id):
	data = session['log']
	purchase = getPurchaseRequestFormData(id)

	sql = "SELECT * FROM items WHERE form_id='{}'".format(purchase[0])
	g.cur.execute(sql)
	items = g.cur.fetchall()
	
	if data[8] == "OFFICE HEAD" or data[8] == 'DEPARTMENT HEAD' or data[8] == 'DEAN':
		return render_template("head/own_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "BUDGET CLERK":
		return render_template("bc/own_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "FINANCE HEAD":
		return render_template("fh/own_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "SCHOOL PRESIDENT":
		return render_template("sp/own_purchase_request_form.html",data=data,purchase=purchase,items=items)
	elif data[8] == "PMO":
		return render_template("pmo/own_purchase_request_form.html",data=data,purchase=purchase,items=items)
	else:
		return render_template("employee/own_purchase_request_form.html",data=data,purchase=purchase,items=items)

# --------------------------------------------- END HEAD -------------------------------------------- #

# --------------------------------------------- BUDGET CLERK -------------------------------------------- #

@app.route("/bc_approve_petty_cash_form/<int:id>")
def bc_approve_petty_cash_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']

	sql = "UPDATE petty_cash SET budget_clerk='{} {}', status='SCHOOL ACCOUNTANT', bc_sig='{}' WHERE id='{}'".format(data[1],data[2],data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM petty_cash WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Petty Cash Approved by {} {} Pending for School Accountant".format(data[1],data[2])
	send_email(_message,email)

	_message = "New Petty Cash waiting for Finance Head Approval"
	sendGroupEmail(_message,"SCHOOL ACCOUNTANT")
	return jsonify({'data': 'success', 'route': 'incoming'})

@app.route("/bc_approve_purchase_request_form/<int:id>",methods=['POST'])
def bc_approve_purchase_request_forms(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	charge_to_the_account_of = request.form['charge_to_the_account_of']
	budget_allocation = request.form['budget_allocation']
	date_of_utilization = request.form['date_of_utilization']
	account_code = request.form['account_code']
	budget_remaining = request.form['budget_remaining']

	pr_type = request.form['pr_type']

	if pr_type == 'Item':
		if request.files.get('file', None):
			image = request.files['file']
			print(image)
			image_filename = secure_filename(image.filename)
			image.save(os.path.join(UPLOAD_FOLDER, image_filename))
		else:
			image_filename = None
	
	person = "{} {}".format(data[1],data[2])
	today = currentDate.strftime("%m/%d/%Y")

	if pr_type == 'Item':
		sql = "UPDATE purchase_request SET status='SCHOOL ACCOUNTANT', charge_to_account='{}', budget_allocation='{}', date_of_utilization='{}', account_code='{}', budget_remaining='{}', budget_clerk='{}', budget_clerk_date='{}', bc_file_path='{}', bc_sig='{}' WHERE id='{}'".format(charge_to_the_account_of,budget_allocation,date_of_utilization,account_code,budget_remaining,person,today,image_filename,data[11],id)
	else:
		sql = "UPDATE purchase_request SET status='SCHOOL ACCOUNTANT', charge_to_account='{}', budget_allocation='{}', date_of_utilization='{}', account_code='{}', budget_remaining='{}', budget_clerk='{}', budget_clerk_date='{}', bc_sig='{}' WHERE id='{}'".format(charge_to_the_account_of,budget_allocation,date_of_utilization,account_code,budget_remaining,person,today,data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM purchase_request WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Purchase Request Approved by {} Pending for Finance Head".format(person)
	send_email(_message,email)
	# sendMessage(_message,_id)

	_message = "New Purchase Request waiting for Finance Head Approval"
	sendGroupEmail(_message,"FINANCE HEAD")
	# sendGroupMessage(_message,"FINANCE HEAD")
	return jsonify({'data': 'success', 'route': 'incoming'})

# --------------------------------------------- END BUDGET CLERK -------------------------------------------- #

# --------------------------------------------- SCHOOL ACCOUNTANT -------------------------------------------- #

@app.route("/sa_approve_petty_cash_form/<int:id>")
def sa_approve_petty_cash_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']

	sql = "UPDATE petty_cash SET school_accountant='{} {}', status='FINANCE HEAD', sa_sig='{}' WHERE id='{}'".format(data[1],data[2],data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM petty_cash WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]
	
	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Petty Cash Approved by {} {} School Accountant".format(data[1],data[2])
	send_email(_message, email)
	
	_message = "Purchase Request Pending Approval from Finance Head"
	# sendGroupMessage(_message,"SCHOOL PRESIDENT")
	sendGroupEmail(_message, "FINANCE HEAD")
	# _message = "You can now get your budget to the Finance Office"
	# sendMessage(_message,_id)
	return jsonify({'data': 'success', 'route': 'incoming'})
	
@app.route("/sa_approve_purchase_request_form/<int:id>")
def sa_approve_purchase_request_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	person = "{} {}".format(data[1],data[2])
	today = currentDate.strftime("%m/%d/%Y")

	sql = "UPDATE purchase_request SET status='FINANCE HEAD', school_accountant='{}', school_accountant_date='{}', sa_sig='{}' WHERE id='{}'".format(person,today,data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	_message = "Purchase Request Pending Approval from Finance Head"
	# sendGroupMessage(_message,"SCHOOL PRESIDENT")
	sendGroupEmail(_message, "FINANCE HEAD")
	return jsonify({'data': 'success', 'route': 'incoming'})

# --------------------------------------------- END SCHOOL ACCOUNTANT -------------------------------------------- #

# --------------------------------------------- FINANCE HEAD CLERK -------------------------------------------- #

@app.route("/fh_approve_petty_cash_form/<int:id>")
def fh_approve_petty_cash_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']

	sql = "UPDATE petty_cash SET finance_head='{} {}', status='APPROVED', fh_sig='{}' WHERE id='{}'".format(data[1],data[2],data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM petty_cash WHERE id='{}'".format(id)
	g.cur.execute(sql)
	_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	# _message = "Petty Cash Approved by {} {} Finance Head".format(data[1],data[2])
	_message = "You can now get your budget to the Finance Office"
	send_email(_message,email)
	return jsonify({'data': 'success', 'route': 'incoming'})

@app.route("/fh_approve_purchase_request_form/<int:id>")
def fh_approve_purchase_request_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	person = "{} {}".format(data[1],data[2])
	today = currentDate.strftime("%m/%d/%Y")

	sql = "UPDATE purchase_request SET status='SCHOOL PRESIDENT', finance_head='{}', finance_head_date='{}', fh_sig='{}' WHERE id='{}'".format(person,today,data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	_message = "Purchase Request Pending Approval from School President"
	# sendGroupMessage(_message,"SCHOOL PRESIDENT")
	sendGroupEmail(_message,"SCHOOL PRESIDENT")
	return jsonify({'data': 'success', 'route': 'incoming'})

# --------------------------------------------- END FINANCE HEAD CLERK -------------------------------------------- #

# --------------------------------------------- SCHOOL PRESIDENT -------------------------------------------- #

@app.route("/sp_approve_purchase_request_form/<int:id>")
def sp_approve_purchase_request_form(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	person = "{} {}".format(data[1],data[2])
	today = currentDate.strftime("%m/%d/%Y")

	sql = "UPDATE purchase_request SET status='APPROVED', school_president='{}', school_president_date='{}', sp_sig='{}' WHERE id='{}'".format(person,today,data[11],id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM purchase_request WHERE id='{}'".format(id)
	g.cur.execute(sql)
	user_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(user_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "YOUR PURCHASE REQUEST HAS BEEN APPROVED BY {}".format(person)
	# sendMessage(_message,user_id)
	send_email(_message, email)
	return jsonify({'data': 'success', 'route': 'incoming'})

# --------------------------------------------- END SCHOOL PRESIDENT -------------------------------------------- #

# --------------------------------------------- CASHIER -------------------------------------------- #

@app.route("/cashier_received/<int:id>",methods=['POST'])
def cashier_received(id):
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	person = "{} {}".format(data[1],data[2])
	remarks = "RELEASED BY Cashier with the following remarks " +request.form['inputValue']

	sql = "UPDATE petty_cash SET remarks='{}' WHERE id='{}'".format(remarks,id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT user_id FROM petty_cash WHERE id='{}'".format(id)
	g.cur.execute(sql)
	user_id = g.cur.fetchall()[0][0]

	sql = "SELECT email FROM accounts WHERE id='{}'".format(user_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0][0]

	_message = "Your request has been released by the cashier."
	send_email(_message,email)
	return jsonify({'data': 'success', 'route': 'incoming'})

# --------------------------------------------- END CASHIER -------------------------------------------- #

# --------------------------------------------- PMO -------------------------------------------- #

@app.route("/canvass_form")
def canvass_form():
	if 'log' not in session:
		return redirect(url_for("login"))
	data = session['log']
	return render_template("pmo/generate_canvass_form.html", data=data)

@app.route("/view_canvass_form/<int:id>")
def view_canvass_form(id):
	data = session['log']
	purchase = getPurchaseRequestFormData(id)

	sql = "SELECT * FROM items WHERE form_id='{}'".format(purchase[0])
	g.cur.execute(sql)
	items = g.cur.fetchall()
	
	return render_template("pmo/view_canvass_form.html",data=data,purchase=purchase,items=items)

# --------------------------------------------- END PMO -------------------------------------------- #

# ------------------------------------------ ADMIN -------------------------------------- #

@app.route("/report")
def report():
	if 'log' not in session:
		return redirect(url_for("routing"))
	data = session['log']
	today = date.today()
	year = today.year

	sql = ''' SELECT * FROM petty_cash
				JOIN accounts ON petty_cash.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department '''
	g.cur.execute(sql)
	petty_cash = g.cur.fetchall()
	
	sql = ''' SELECT * FROM purchase_request
				JOIN accounts ON purchase_request.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department '''
	g.cur.execute(sql)
	purchase_request = g.cur.fetchall()

	sql = ''' SELECT * FROM department_office WHERE status = 'Active' '''
	g.cur.execute(sql)
	department = g.cur.fetchall()
	
	return render_template("fh/report.html",data=data,petty_cash=petty_cash,purchase_request=purchase_request, filter_type=year, department=department)

@app.route("/filter_report",methods=['POST'])
def filter_report():
	if 'log' not in session:
		return redirect(url_for("routing"))
	filter_type = ""
	data = session['log']
	year = request.form['year']

	if "month" in request.form and "department" in request.form and "status" in request.form:
		month = request.form['month']
		department = request.form['department']
		status = request.form['status']

		if status != 'PENDING':
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and strftime('%m',petty_cash.date) = '{}' and department_office.department = '{}' and petty_cash.status = '{}' '''.format(year,month,department,status)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and strftime('%m',purchase_request.date) = '{}' and department_office.department = '{}' and purchase_request.status = '{}' '''.format(year,month,department,status)
		else:
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and strftime('%m',petty_cash.date) = '{}' and department_office.department = '{}' and petty_cash.status != 'APPROVED' and petty_cash.status != 'CANCELLED' and petty_cash.status != 'DISAPPROVED' '''.format(year,month,department)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and strftime('%m',purchase_request.date) = '{}' and department_office.department = '{}' and purchase_request.status != 'APPROVED' and purchase_request.status != 'CANCELLED' and purchase_request.status != 'DISAPPROVED' '''.format(year,month,department)

		g.cur.execute(sql1)
		petty_cash = g.cur.fetchall()
		g.cur.execute(sql2)
		purchase_request = g.cur.fetchall()
		
		if month == '01': month = 'January'
		if month == '02': month = 'February'
		if month == '03': month = 'March'
		if month == '04': month = 'April'
		if month == '05': month = 'May'
		if month == '06': month = 'June'
		if month == '07': month = 'July'
		if month == '08': month = 'August'
		if month == '09': month = 'September'
		if month == '10': month = 'October'
		if month == '11': month = 'November'
		if month == '12': month = 'December'
		filter_type = month + ' ' + year + ' ' + department + '-' + status

	elif "month" in request.form and "department" in request.form:
		month = request.form['month']
		department = request.form['department']
		sql = ''' SELECT * FROM petty_cash
				JOIN accounts ON petty_cash.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',petty_cash.date) = '{}' and strftime('%m',petty_cash.date) = '{}' and department_office.department = '{}' '''.format(year,month,department)
		g.cur.execute(sql)
		petty_cash = g.cur.fetchall()

		sql = ''' SELECT * FROM purchase_request
				JOIN accounts ON purchase_request.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',purchase_request.date) = '{}' and strftime('%m',purchase_request.date) = '{}' and department_office.department = '{}' '''.format(year,month,department)
		g.cur.execute(sql)
		purchase_request = g.cur.fetchall()
		
		if month == '01': month = 'January'
		if month == '02': month = 'February'
		if month == '03': month = 'March'
		if month == '04': month = 'April'
		if month == '05': month = 'May'
		if month == '06': month = 'June'
		if month == '07': month = 'July'
		if month == '08': month = 'August'
		if month == '09': month = 'September'
		if month == '10': month = 'October'
		if month == '11': month = 'November'
		if month == '12': month = 'December'
		filter_type = month + ' ' + year + ' ' + department

	elif "department" in request.form and "status" in request.form:
		department = request.form['department']
		status = request.form['status']
		if status != 'PENDING':
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and department_office.department = '{}' and petty_cash.status = '{}' '''.format(year,department,status)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and department_office.department = '{}' and purchase_request.status = '{}' '''.format(year,department,status)
		else:
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and department_office.department = '{}' and petty_cash.status != 'APPROVED' and petty_cash.status != 'CANCELLED' and petty_cash.status != 'DISAPPROVED' '''.format(year,department)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and department_office.department = '{}' and purchase_request.status != 'APPROVED' and purchase_request.status != 'CANCELLED' and purchase_request.status != 'DISAPPROVED' '''.format(year,department)
		
		g.cur.execute(sql1)
		petty_cash = g.cur.fetchall()
	
		g.cur.execute(sql2)
		purchase_request = g.cur.fetchall()
		filter_type = year + ' ' + department + '-' + status
	
	elif "month" in request.form:
		month = request.form['month']
		sql = ''' SELECT * FROM petty_cash
				JOIN accounts ON petty_cash.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',petty_cash.date) = '{}' and strftime('%m',petty_cash.date) = '{}' '''.format(year,month)
		g.cur.execute(sql)
		petty_cash = g.cur.fetchall()
	
		sql = ''' SELECT * FROM purchase_request
				JOIN accounts ON purchase_request.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',purchase_request.date) = '{}' and strftime('%m',purchase_request.date) = '{}' '''.format(year,month)
		g.cur.execute(sql)
		purchase_request = g.cur.fetchall()
		filter_type = month + ' ' + year
	
	elif "department" in request.form:
		department = request.form['department']
		sql = ''' SELECT * FROM petty_cash
				JOIN accounts ON petty_cash.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',petty_cash.date) = '{}' and department_office.department = '{}' '''.format(year,department)
		g.cur.execute(sql)
		petty_cash = g.cur.fetchall()
	
		sql = ''' SELECT * FROM purchase_request
				JOIN accounts ON purchase_request.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',purchase_request.date) = '{}' and department_office.department = '{}' '''.format(year,department)
		g.cur.execute(sql)
		purchase_request = g.cur.fetchall()
		filter_type = year + ' ' + department
		
	elif "status" in request.form:
		status = request.form['status']
		
		if status != 'PENDING':
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and petty_cash.status = '{}' '''.format(year,status)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and purchase_request.status = '{}' '''.format(year,status)
		else:
			sql1 = ''' SELECT * FROM petty_cash
					JOIN accounts ON petty_cash.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',petty_cash.date) = '{}' and petty_cash.status != 'APPROVED' and petty_cash.status != 'CANCELLED' and petty_cash.status != 'DISAPPROVED' '''.format(year)
			
			sql2 = ''' SELECT * FROM purchase_request
					JOIN accounts ON purchase_request.user_id = accounts.id
					JOIN department_office ON department_office.id = accounts.department 
					WHERE strftime('%Y',purchase_request.date) = '{}' and purchase_request.status != 'APPROVED' and purchase_request.status != 'CANCELLED' and purchase_request.status != 'DISAPPROVED' '''.format(year)
		g.cur.execute(sql1)
		petty_cash = g.cur.fetchall()
	
		g.cur.execute(sql2)
		purchase_request = g.cur.fetchall()

		filter_type = year + ' ' + status

	else:
		sql = ''' SELECT * FROM petty_cash
				JOIN accounts ON petty_cash.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',petty_cash.date) = '{}' '''.format(year)
		g.cur.execute(sql)
		petty_cash = g.cur.fetchall()
	
		sql = ''' SELECT * FROM purchase_request
				JOIN accounts ON purchase_request.user_id = accounts.id
				JOIN department_office ON department_office.id = accounts.department 
				WHERE strftime('%Y',purchase_request.date) = '{}' '''.format(year)
		g.cur.execute(sql)
		purchase_request = g.cur.fetchall()
		
		filter_type = year
	
	sql = ''' SELECT * FROM department_office WHERE status = 'Active' '''
	g.cur.execute(sql)
	department = g.cur.fetchall()
	
	return render_template("fh/report.html",data=data,petty_cash=petty_cash,purchase_request=purchase_request, filter_type=filter_type, department=department)


@app.route("/fetch_petty_cash_per_month",methods=['POST'])
def fetch_petty_cash_per_month():
	if 'log' not in session:
		return redirect(url_for("routing"))
	year = request.form['data']
	sql = '''SELECT month_number, count(petty_cash.id) as total FROM month
					LEFT JOIN petty_cash ON strftime('%m', date) = month_number and strftime('%Y', date) = '{}'
					GROUP BY month_number
					ORDER BY month_number; '''.format(year)
	g.cur.execute(sql)
	count_petty_cash = g.cur.fetchall()
	return json.dumps(count_petty_cash)

@app.route("/fetch_purchase_request_per_month",methods=['POST'])
def fetch_purchase_request_per_month():
	if 'log' not in session:
		return redirect(url_for("routing"))
	year = request.form['data']
	sql = '''SELECT month_number, count(purchase_request.id) as total FROM month
				LEFT JOIN purchase_request ON strftime('%m', date) = month_number and strftime('%Y', date) = '{}'
				GROUP BY month_number
				ORDER BY month_number; '''.format(year)
	print(sql)
	g.cur.execute(sql)
	count_purchase_request = g.cur.fetchall()
	return json.dumps(count_purchase_request)

@app.route("/view_employees")
def view_employees():
	if 'log' not in session:
		return redirect(url_for("routing"))

	sql = '''SELECT * FROM accounts
			JOIN department_office ON accounts.department = department_office.id WHERE NOT account='ADMIN';'''
	g.cur.execute(sql)
	data= g.cur.fetchall()
	
	sql = "SELECT * FROM department_office WHERE status = 'Active'"
	g.cur.execute(sql)
	department = g.cur.fetchall()
	
	return render_template("view_employees.html",data=data,department=department)

@app.route("/add_user",methods=['POST'])
def add_user():
	fname = request.form['fname'].title()
	lname = request.form['lname'].title()
	contact = request.form['contact']
	account = request.form['account']
	address = request.form['address']
	email = request.form['email']
	username = ("{}{}{}".format(fname[0],lname,contact[-2:])).lower()
	password = "12345678"
	department = request.form['department']
	
	sql = "INSERT INTO accounts(fname,lname,username,password,contact,email,address,account,department,status) VALUES('{}','{}','{}','{}','{}','{}','{}','{}','{}','Active')".format(fname,lname,username,password,contact,email,address,account,department)
	g.cur.execute(sql)
	g.conn.commit()

	return redirect(url_for("view_employees"))

@app.route('/edit_employee',methods=['POST'])
def edit_employee():
	_id = request.form['id']
	department = request.form['department']
	account = request.form['account']
	status = request.form['status']

	sql = "UPDATE accounts SET account = '{}', department = '{}', status ='{}' WHERE id = {}".format(account, department, status, _id)
	g.cur.execute(sql)
	g.conn.commit()

	return redirect(url_for("view_employees"))

@app.route('/upload_signature',methods=['POST'])
def upload_signature():
	_id = request.form['user_id']
	
	if request.files.get('file', None):
		image = request.files['file']
		image_filename = secure_filename(image.filename)
		image.save(os.path.join(UPLOAD_FOLDER, image_filename))
	else:
		image_filename = None

	sql = "UPDATE accounts SET file_path = '{}' WHERE id = '{}'".format(image_filename, _id)
	g.cur.execute(sql)
	g.conn.commit()
	return redirect(url_for("view_employees"))

@app.route('/reset_password/<int:user_id>',methods=['GET'])
def reset_password(user_id):
	random_pass = ''.join(random.choices(string.ascii_lowercase, k=6))
	sql = "UPDATE accounts SET password = '{}', status = 'Active' WHERE id = '{}'".format(random_pass, user_id)
	g.cur.execute(sql)
	g.conn.commit()

	sql = "SELECT email FROM accounts WHERE id = '{}' LIMIT 1".format(user_id)
	g.cur.execute(sql)
	email = g.cur.fetchall()[0]

	message = '''
			<html><body>
			<div>
				<div class="text-center" style="font-size: 17px;">
					Saint Michael College of Caraga <br>
					<p>Good day user, Our admins has verified your request here is your new password: <b>{}<b>. Please change it as soon as possible. Thank you</p>
				</div>
			</div>
			</body></html>
		'''.format(random_pass)
	send_email(message, email)
	return jsonify({'data': 'success', 'route': 'view_employees'})

@app.route('/verify_account/<int:user_id>/<email>',methods=['GET'])
def verify_account(user_id, email):
	sql = "UPDATE accounts SET status = 'Active' WHERE id = '{}'".format(user_id)
	g.cur.execute(sql)
	g.conn.commit()

	message = '''
			<html><body>
			<div>
				<div class="text-center" style="font-size: 17px; font-weight: bolder;">
					Saint Michael College of Caraga <br>
					<p>Good day user, this is to inform you that your account has been successfully verified by our admins. You can now access the system. Thank you</p>
				</div>
			</div>
			</body></html>
		'''
	send_email(message, email)
	return jsonify({'data': 'success'})

@app.route("/view_department_office")
def view_department_office():
	if 'log' not in session:
		return redirect(url_for("routing"))

	sql = "SELECT * FROM department_office"
	g.cur.execute(sql)
	data= g.cur.fetchall()

	return render_template("view_departments.html",data=data)

@app.route('/add_department',methods=['POST'])
def add_department():
	department = request.form['department']

	sql = "INSERT INTO department_office (department, status) VALUES('{}','Active')".format(department)
	g.cur.execute(sql)
	g.conn.commit()

	return redirect(url_for("view_department_office"))

@app.route('/edit_department',methods=['POST'])
def edit_department():
	_id = request.form['id']
	department = request.form['department']
	status = request.form['status']

	sql = "UPDATE department_office SET department = '{}', status = '{}' WHERE id = '{}'".format(department, status, _id)
	g.cur.execute(sql)
	g.conn.commit()

	return redirect(url_for("view_department_office"))

# ------------------------------------------ END ADMIN -------------------------------------- #

def send_email(message, emails):
	email = 'financeofficesmcc@gmail.com'
	password = 'cgzsfhhcmaduvqdu'

	msg = MIMEMultipart()
	msg['From'] = email
	if type(emails) == str:
		msg['To'] = emails
	else:
		msg['To'] = ", ".join(emails)

	msg['Subject'] = 'System Generated Message'
	msg.attach(MIMEText(message, 'html'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(email, password)
	text = msg.as_string()
	server.sendmail(email, emails, text)
	server.quit()

	print("success")

def sendGroupEmail(message,account):
	sql = "SELECT email FROM accounts WHERE account='{}'".format(account)
	g.cur.execute(sql)
	emails = [i[0] for i in g.cur.fetchall()]
	print(emails)
	if emails:
		email = 'financeofficesmcc@gmail.com'
		password = 'cgzsfhhcmaduvqdu'

		msg = MIMEMultipart()
		msg['From'] = email
		if type(emails) == str:
			msg['To'] = emails
		else:
			msg['To'] = ", ".join(emails)

		msg['Subject'] = 'System Generated Message'
		msg.attach(MIMEText(message, 'html'))

		server = smtplib.SMTP('smtp.gmail.com', 587)
		server.starttls()
		server.login(email, password)
		text = msg.as_string()
		server.sendmail(email, emails, text)
		server.quit()

	print("success")

def getPendingRequestsCount(table, account_type, dept):
	if account_type == "OFFICE HEAD" or account_type == 'DEPARTMENT HEAD' or account_type == 'DEAN':
		if table == "petty_cash":
			sql = "SELECT count(*) FROM {} JOIN accounts ON petty_cash.user_id = accounts.id WHERE department = '{}' and petty_cash.status = 'HEAD'".format(table, dept)
		else:
			sql = "SELECT count(*) FROM {} JOIN accounts ON purchase_request.user_id = accounts.id WHERE department = '{}' and purchase_request.status = 'HEAD'".format(table, dept)
	else: 
		sql = "SELECT count(*) FROM {} WHERE status = '{}'".format(table, account_type)
	g.cur.execute(sql)
	return g.cur.fetchall()[0]

def getOwnRequestsCount(table, status, id):
	if status == 'APPROVED' or status == 'DISAPPROVED':
		sql = "SELECT count(*) FROM {} WHERE status = '{}' and user_id = '{}'".format(table, status, id)
	else:
		sql = "SELECT count(*) FROM {} WHERE user_id = '{}'".format(table, id)

	g.cur.execute(sql)
	return g.cur.fetchall()[0]

def getMyForms(id, form_type):
	if form_type == 'Petty Cash':
		sql = "SELECT * FROM petty_cash WHERE user_id = '{}'".format(id)
	elif form_type == 'Purchase Request':
		sql = "SELECT * FROM purchase_request WHERE user_id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()

def getPettyCashForms(account_type):
	if account_type == 'ADMIN':
		sql = "SELECT * FROM leave_form WHERE status='APPROVED'"
	
	elif account_type == 'OFFICE HEAD' or account_type == 'DEPARTMENT HEAD' or account_type == 'DEAN':
		dept = session['log'][9]
		sql = "SELECT * FROM petty_cash JOIN accounts ON petty_cash.user_id = accounts.id WHERE department = '{}' and petty_cash.status = 'HEAD'".format(dept)
	elif account_type == 'BUDGET CLERK':
		sql = "SELECT * FROM petty_cash WHERE status='BUDGET CLERK'"
	elif account_type == 'SCHOOL ACCOUNTANT':
		sql = "SELECT * FROM petty_cash WHERE status='SCHOOL ACCOUNTANT'"
	elif account_type == 'CASHIER':
		sql = "SELECT * FROM petty_cash WHERE status='APPROVED'"
	elif account_type == 'FINANCE HEAD':
		sql = "SELECT * FROM petty_cash WHERE status='FINANCE HEAD'"
	else:
		id = session['log'][0]
		sql = "SELECT * FROM petty_cash WHERE user_id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()

def getPettyCashOutgoingForms(account_type):
	if account_type == 'ADMIN':
		sql = "SELECT * FROM leave_form WHERE status='APPROVED'"
	
	elif account_type == 'OFFICE HEAD' or account_type == 'DEPARTMENT HEAD' or account_type == 'DEAN':
		dept = session['log'][9]
		sql = "SELECT * FROM petty_cash JOIN accounts ON petty_cash.user_id = accounts.id WHERE department = '{}' and petty_cash.status != 'HEAD'".format(dept)
	elif account_type == 'BUDGET CLERK':
		sql = "SELECT * FROM petty_cash WHERE status != 'HEAD' and status != 'BUDGET CLERK'"
	elif account_type == 'SCHOOL ACCOUNTANT':
		sql = "SELECT * FROM petty_cash WHERE status = 'FINANCE HEAD'"
	elif account_type == 'FINANCE HEAD':
		sql = "SELECT * FROM petty_cash WHERE status == 'APPROVED' or status == 'DISAPPROVED'"
	else:
		id = session['log'][0]
		sql = "SELECT * FROM petty_cash WHERE user_id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()

def getPurchaseRequestForms(account_type):
	if account_type == 'ADMIN':
		sql = "SELECT * FROM leave_form WHERE status='APPROVED'"
	elif account_type == 'OFFICE HEAD' or account_type == 'DEPARTMENT HEAD' or account_type == 'DEAN':
		dept = session['log'][9]
		sql = "SELECT * FROM purchase_request JOIN accounts ON purchase_request.user_id = accounts.id WHERE department = '{}' and purchase_request.status = 'HEAD'".format(dept)
	elif account_type == 'BUDGET CLERK':
		sql = "SELECT * FROM purchase_request WHERE status='BUDGET CLERK'"
	elif account_type == 'SCHOOL ACCOUNTANT':
		sql = "SELECT * FROM purchase_request WHERE status='SCHOOL ACCOUNTANT'"
	elif account_type == 'FINANCE HEAD':
		sql = "SELECT * FROM purchase_request WHERE status='FINANCE HEAD'"
	elif account_type == 'SCHOOL PRESIDENT':
		sql = "SELECT * FROM purchase_request WHERE status='SCHOOL PRESIDENT'"
	elif account_type == 'PMO':
		sql = "SELECT * FROM purchase_request WHERE status='APPROVED'"
	else:
		id = session['log'][0]
		sql = "SELECT * FROM purchase_request WHERE user_id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()

def getPurchaseRequestOutgoingForms(account_type):
	if account_type == 'ADMIN':
		sql = "SELECT * FROM leave_form WHERE status='APPROVED'"
	elif account_type == 'OFFICE HEAD' or account_type == 'DEPARTMENT HEAD' or account_type == 'DEAN':
		dept = session['log'][9]
		sql = "SELECT * FROM purchase_request JOIN accounts ON purchase_request.user_id = accounts.id WHERE department = '{}' and purchase_request.status != 'HEAD'".format(dept)
	elif account_type == 'BUDGET CLERK':
		sql = "SELECT * FROM purchase_request WHERE status != 'HEAD' and status != 'BUDGET CLERK'"
	elif account_type == 'SCHOOL ACCOUNTANT':
		sql = "SELECT * FROM purchase_request WHERE status != 'HEAD' and status != 'BUDGET CLERK' and status != 'SCHOOL ACCOUNTANT'"
	elif account_type == 'FINANCE HEAD':
		sql = "SELECT * FROM purchase_request WHERE status != 'HEAD' and status != 'BUDGET CLERK' and status != 'SCHOOL ACCOUNTANT' and status != 'FINANCE HEAD'"
	elif account_type == 'SCHOOL PRESIDENT':
		sql = "SELECT * FROM purchase_request WHERE status == 'APPROVED' or status == 'DISAPPROVED'"
	else:
		id = session['log'][0]
		sql = "SELECT * FROM purchase_request WHERE user_id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()

def getPettyCashFormData(id):
	sql = "SELECT * FROM petty_cash WHERE id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()[0]

def getPurchaseRequestFormData(id):
	sql = "SELECT * FROM purchase_request WHERE id = '{}'".format(id)
	g.cur.execute(sql)
	return g.cur.fetchall()[0]

def sendGroupMessage(_message,account):

	sql = "SELECT contact FROM accounts WHERE account='{}'".format(account)
	g.cur.execute(sql)
	contacts = g.cur.fetchall()

	
	for i in contacts:
		contact = "+63{}".format(i[0][1::])
		message = client.messages.create(
			body=_message,
			from_="+12232176530",
			to=contact
		)

def sendMessage(_message,_id):
	sql = "SELECT contact FROM accounts WHERE id='{}'".format(_id)
	g.cur.execute(sql)
	contact = g.cur.fetchall()[0][0]
	contact = "+63{}".format(contact[1::])
	message = client.messages.create(
		body=_message,
		from_="+12232176530",
		to=contact
	)

@app.context_processor
def own_purchase_request_cnt():
	if 'log' in session:
		data = session['log']
	
		approve_purchase_request = getOwnRequestsCount('purchase_request', "APPROVED", data[0])
		disapprove_purchase_request = getOwnRequestsCount('purchase_request', "DISAPPROVED", data[0])
		return dict(own_approve_purchase_request_cnt=approve_purchase_request[0], own_disapprove_purchase_request_cnt=disapprove_purchase_request[0])
	else:
		return dict(own_approve_purchase_request_cnt="0", own_disapprove_purchase_request_cnt="0")

@app.context_processor
def own_petty_cash_cnt():
	if 'log' in session:
		data = session['log']
	
		approve_petty_cash = getOwnRequestsCount('petty_cash', "APPROVED", data[0])
		disapprove_petty_cash = getOwnRequestsCount('petty_cash', "DISAPPROVED", data[0])
		return dict(own_approve_petty_cash_cnt=approve_petty_cash[0], own_disapprove_petty_cash_cnt=disapprove_petty_cash[0])
	else:
		return dict(own_approve_petty_cash_cnt="0", own_disapprove_petty_cash_cnt="0")

@app.context_processor
def purchase_request_cnt():
	if 'log' in session:
		data = session['log']
	
		pending_purchase_request = getPendingRequestsCount('purchase_request', data[8], data[9])
		_message = str(pending_purchase_request[0])
		return dict(purchase_request_cnt=_message)
	else:
		return dict(purchase_request_cnt="0")

@app.context_processor
def petty_cash_cnt():
	if 'log' in session:
		data = session['log']
	
		pending_petty_cash = getPendingRequestsCount('petty_cash', data[8], data[9])
		_message = str(pending_petty_cash[0])
		return dict(petty_cash_cnt=_message)
	else:
		return dict(petty_cash_cnt="0")

if __name__ == "__main__":
	app.run(debug=True, host='0.0.0.0')