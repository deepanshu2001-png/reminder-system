
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, SelectField, RadioField, validators
from wtforms.fields import DateField

from passlib.hash import sha256_crypt
from functools import wraps
from datetime import *
import datetime as dt
import time

app = Flask(__name__) # Initializing the app
app.secret_key = "99ae7ad851d25b451412a836eedcdc3f91e1da178e207fc9" #Generated Secret Key

#Configuring database
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Deepanshu@123'
app.config['MYSQL_DB'] = 'reminder_system'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


# User Registration
class Registration(Form):
	reg_name = StringField('Name',[validators.Length(min=5,max=40), validators.DataRequired()])
	reg_password = PasswordField('Password',[validators.Length(min=5,max=100), validators.DataRequired(), validators.EqualTo('reg_confirm', message='Password do not match')])
	reg_confirm = PasswordField('Confirm Password')

@app.route('/', methods=['GET','POST']) # Home route
def register():
	form = Registration(request.form)
	if request.method == 'POST' and form.validate():
		reg_name = form.reg_name.data
		
		reg_password = sha256_crypt.encrypt(str(form.reg_password.data))

		cur = mysql.connection.cursor()
		cur.execute('INSERT INTO registration(NAME,PASSWORD) VALUES (%s,%s)',(reg_name,reg_password))
		mysql.connection.commit()
		cur.close()

		flash('Registration successfull !!','success')
		return redirect(url_for('register'))
		
	return render_template('index.html',form=form)



# User Login
@app.route('/login', methods=['POST'])
def login():
	if request.method == 'POST':
		log_name = request.form['Name']
		password_temp = request.form['Password']
		cur = mysql.connection.cursor()
		result = cur.execute('SELECT * FROM registration WHERE NAME=%s',[log_name])

		if result>0:
			value = cur.fetchone()
			password = value['PASSWORD']
			if sha256_crypt.verify(password_temp,password):
				session['logged_in'] = True
				session['username'] = value['NAME'] #Retrieving username from database for session
				session['UID'] = value['UID']
				return redirect(url_for('home'))
			else:
				form = Registration(request.form)
				return render_template('index.html', form=form, error='Incorrect Password, Please Try Again')
			cur.close()
		else:
			form = Registration(request.form)
			return render_template('index.html', form=form, error='Email not found, Please Try Again')

# #Checking if session is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized attempt, Please Login','danger')
			return redirect(url_for('register'))
	return wrap

# # Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('Logged out Succesfully','success')
	return redirect(url_for('register'))

# Home Page
@app.route('/home')
@is_logged_in
def home():
	return render_template('home.html', day=datetime.today().strftime('%A'), date=datetime.today().strftime('%B %d, %Y'))

# Set Reminder
class Set_Reminder(Form):
	date = DateField('Date', [validators.DataRequired()], format='%Y-%m-%d')
	subject = SelectField(label='Subject',choices=[('Event','Event'),('Birthday','Birthday'),('Aniversary','Aniversary')])
	description = StringField('Add Description',[validators.DataRequired()])
	contact_val = StringField('',render_kw={'placeholder':'Enter value of selected field'})

@app.route('/home/set_reminder',methods=['GET','POST'])
@is_logged_in
def set_reminder():
	form = Set_Reminder(request.form)
	if request.method=='POST' and form.validate():
		recur = [0]*4
		Uid = request.form['unique']
		date = form.date.data
		subject = form.subject.data
		description = form.description.data
		contact_val = form.contact_val.data
		recur7,recur5,recur3,recur2 = request.form.getlist('recur7'),request.form.getlist('recur5'),request.form.getlist('recur3'),request.form.getlist('recur2')
		recur = [int(recur7[0]) if len(recur7)!=0 else 0,int(recur5[0]) if len(recur5)!=0 else 0,int(recur3[0]) if len(recur3)!=0 else 0,int(recur2[0]) if len(recur2)!=0 else 0]

		cur = mysql.connection.cursor()
		if not all(v==0 for v in recur):
			cur.execute('INSERT INTO recur(DAY_7,DAY_5,DAY_3,DAY_2) VALUES(%s,%s,%s,%s)',(recur[0],recur[1],recur[2],recur[3]))
			x = cur.execute('SELECT MAX(RECUR_NEXT) AS RECUR_NEXT FROM recur')
			recur_next = cur.fetchone()
			cur.execute('INSERT INTO set_reminder(UID,DATE,SUBJECT,DESCRIPTION,CONTACT,RECUR_NEXT) VALUES(%s,%s,%s,%s,%s,%s)',(Uid,date,subject,description,contact_val,recur_next['RECUR_NEXT']))
		else:
			cur.execute('INSERT INTO set_reminder(UID,DATE,SUBJECT,DESCRIPTION,CONTACT) VALUES(%s,%s,%s,%s,%s,%s)',(Uid,date,subject,description,contact_val))
		mysql.connection.commit()
		cur.close()
		flash('Reminder Added','success')
		return redirect(url_for('set_reminder'))
	return render_template('set_reminder.html',form=form)

# View reminders
class View_Reminder(Form):
	date = DateField('Start Date', format='%Y-%m-%d')
	subject = SelectField(label='Subject',choices=[('Event','Event'),('Birthday','Birthday'),('Aniversary','Aniversary')])

@app.route('/home/view_reminder',methods=['GET','POST'])
@is_logged_in
def view_reminder():
	form = View_Reminder(request.form)
	cur = mysql.connection.cursor()
	if request.method=='POST':
		start_date = form.date.data
		subject = form.subject.data
		result = cur.execute('SELECT DATE,SUBJECT,DESCRIPTION,CONTACT,STATUS,DAY_7,DAY_5,DAY_3,DAY_2 FROM set_reminder INNER JOIN recur ON set_reminder.RECUR_NEXT=recur.RECUR_NEXT and SUBJECT=%s and DATE=%s and UID = %s',(subject,start_date,session['UID']))
	else:
		result = cur.execute('SELECT DATE,SUBJECT,DESCRIPTION,CONTACT,STATUS,DAY_7,DAY_5,DAY_3,DAY_2 FROM set_reminder INNER JOIN recur ON set_reminder.RECUR_NEXT=recur.RECUR_NEXT and UID=%s',(session['UID'],))
	data = cur.fetchall()
	if result>0:
		return render_template('view_reminder.html',form=form,data=data)
		cur.close()
	else:
		return render_template('view_reminder.html',form=form,msg='No Reminders')
		cur.close()
	return render_template('view_reminder.html',form=form)

# Enable/Disable Reminder
@app.route('/home/enable-disable')
def enable_disable():
	cur = mysql.connection.cursor()
	enable = cur.execute('SELECT DATE,SUBJECT,DESCRIPTION FROM set_reminder WHERE STATUS="ENABLED" and UID=%s',(session['UID'],))
	data1 = cur.fetchall()
	disable = cur.execute('SELECT DATE,SUBJECT,DESCRIPTION FROM set_reminder WHERE STATUS="DISABLED" and UID=%s',(session['UID'],))
	data2 = cur.fetchall()
	if enable>0:
		return render_template('enable-disable.html',data1=data1,data2=data2)
	if disable>0:
		return render_template('enable-disable.html',data1=data1,data2=data2)
	return render_template('enable-disable.html')

# Enable Reminder
@app.route('/enable', methods=['GET','POST'])
@is_logged_in
def enable():
	if request.method=='POST':
		reminders = request.form.get('enable_val')
		x = reminders.split(',')
		cur = mysql.connection.cursor()
		cur.execute('UPDATE set_reminder SET STATUS="ENABLED" WHERE DATE=%s and SUBJECT=%s and DESCRIPTION=%s',(x[0],x[1],x[2]))
		flash('Reminder Enabled','success')
		mysql.connection.commit()
		cur.close()
	return redirect(url_for('enable_disable'))

# Disable Reminder
@app.route('/disable', methods=['GET','POST'])
@is_logged_in
def disable():
	if request.method=='POST':
		reminders = request.form.get('disable_val')
		x = reminders.split(',')
		cur = mysql.connection.cursor()
		cur.execute('UPDATE set_reminder SET STATUS="DISABLED" WHERE DATE=%s and SUBJECT=%s and DESCRIPTION=%s',(x[0],x[1],x[2]))
		flash('Reminder Disabled','danger')
		mysql.connection.commit()
		cur.close()
	return redirect(url_for('enable_disable'))

# Delete Reminder
@app.route('/home/reminder', methods=['GET','POST'])
@is_logged_in
def search_reminder():
	cur = mysql.connection.cursor()
	result = cur.execute('SELECT SUBJECT,DESCRIPTION FROM set_reminder WHERE UID=%s',(session['UID'],))
	data = cur.fetchall()
	if result>0:
		if request.method=='POST':
			date = request.form['date']
			subject = request.form.get('subject')
			reminders = request.form.get('reminders')
			cur1 = mysql.connection.cursor()
			search = cur1.execute('SELECT DATE,SUBJECT,DESCRIPTION,RECUR_NEXT FROM set_reminder WHERE DATE=%s AND SUBJECT=%s AND DESCRIPTION=%s',(date,subject,reminders))
			data1 = cur1.fetchall()
			cur1.close()
			return render_template('reminder.html',data=data,value=data1)
		return render_template('reminder.html',data=data)
	else:
		return render_template('reminder.html',data='No Reminders. Please Add to see in list')
		cur.close()
	return render_template('reminder.html')

@app.route('/home/reminder/delete',methods=['GET','POST'])
@is_logged_in
def delete_reminder():
	if request.method=='POST':
		desc = request.form['description']
		x = desc.split(',')
		cur = mysql.connection.cursor()
		result = cur.execute('SELECT RECUR_NEXT FROM set_reminder WHERE DATE=%s AND SUBJECT=%s AND DESCRIPTION=%s AND UID=%s',(x[0],x[1],x[2],session['UID']))
		value = cur.fetchone()
		cur.execute('DELETE FROM set_reminder WHERE DATE=%s AND SUBJECT=%s AND DESCRIPTION=%s',[x[0],x[1],x[2]])
		cur.execute('DELETE FROM recur WHERE RECUR_NEXT=%s',[value['RECUR_NEXT']])
		flash('Reminder Deleted','danger')
		mysql.connection.commit()
		cur.close()
	return redirect(url_for('search_reminder'))

# Modify Reminders
@app.route('/home/reminder/modify',methods=['GET','POST'])
def modify_reminder():
	if request.method=='POST':
		id_val = request.form['id']
		description = request.form['add_description']
		contact = request.form['add_contact']
		recur7,recur5,recur3,recur2 = request.form.getlist('recur7'),request.form.getlist('recur5'),request.form.getlist('recur3'),request.form.getlist('recur2')
		recur = [int(recur7[0]) if len(recur7)!=0 else 0,int(recur5[0]) if len(recur5)!=0 else 0,int(recur3[0]) if len(recur3)!=0 else 0,int(recur2[0]) if len(recur2)!=0 else 0]
		if description!='' and contact!='' and recur!=([0]*4):
			cur = mysql.connection.cursor()
			cur.execute('UPDATE set_reminder SET DESCRIPTION=%s,CONTACT=%s WHERE RECUR_NEXT=%s',(description,contact,id_val))
			cur.execute('UPDATE recur SET DAY_7=%s,DAY_5=%s,DAY_3=%s,DAY_2=%s WHERE RECUR_NEXT=%s',(recur[0],recur[1],recur[2],recur[3],id_val))
			flash('Modified Succesfully','success')
			mysql.connection.commit()
			cur.close()
			return redirect(url_for('search_reminder'))
		else:
			flash('Please fill all the fields','danger')
			return redirect(url_for('search_reminder'))
	return render_template('reminder.html')

if __name__ == '__main__':
	app.run(debug = True)