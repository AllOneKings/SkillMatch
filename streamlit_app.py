import requests
import streamlit as st # core package used in this project
import pandas as pd
import time
import nltk
import spacy
nltk.download('stopwords')
spacy.load('en_core_web_sm')

import base64, random
import datetime
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io, random
from streamlit_tags import st_tags
from PIL import Image
import pymysql
from pymysql import OperationalError, MySQLError
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import pafy
import plotly.express as px # to create visualisations at the admin session
import yt_dlp
import os
from dotenv import load_dotenv
import socket
import platform
import geocoder
import secrets
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
import re
import logging


st.set_page_config(
    page_title="SkillMatch Resume Analyzer App",
    page_icon='./Logo/SRAA_Logo.ico',
)

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
RAPID_URL = os.getenv("RAPID_URL")
X_RapidAPI_Key = os.getenv("X_RapidAPI_Key")
X_RapidAPI_Host = os.getenv("X_RapidAPI_Host")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
        
# Function to validate email format
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

# Function to validate mobile number using regex
def is_valid_mobile(mobile):
    mobile_regex = r'^\+?(\d{1,4})?[-.\s]?((\d{3,})[-.\s]?){2,}$'
    return re.match(mobile_regex, mobile) is not None

# Function to geocode with retry
def geocode_with_retry(latlng, retries=3, delay=1):
    geolocator = Nominatim(user_agent="http")
    location = None
    
    for attempt in range(retries):
        try:
            location = geolocator.reverse(latlng, language='en', timeout=10)
            if location:
                return location
        except GeopyError as e:
            logger.error(f"Geocoding error: {e}")
            st.error(f"Geocoding error on attempt {attempt + 1}: {e}")
            time.sleep(delay)
    
    return location
        

def fetch_yt_video(link):
    try:
        response = requests.get(link)
        if response.status_code == 200:
            html_content = response.text
            title_match = re.search(r'<title>(.*?) - YouTube</title>', html_content)
            if title_match:
                title = title_match.group(1)
                return title
            else:
                return "Video Title Unavailable"
        else:
            return "Video Title Unavailable"
    except Exception as e:
        return f"Error: {e}"

def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
            print(page)
        text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course

# Function to connect to the database
def connect_to_database():
    try:
        connection = pymysql.connect(host = DB_HOST, user = DB_USER, password = DB_PASSWORD)
        cursor = connection.cursor()
        return connection, cursor
    except pymysql.OperationalError:
        st.error("Sorry, we're currently experiencing some technical difficulties. Please try again later.")
    except pymysql.MySQLError:
        st.error("Sorry, something went wrong with the database. Please try again later.")
    except Exception as e:
        st.error("An unexpected error occurred. Please try again later.")
        logging.error("Unexpected error: %s", e)
    return None, None

# Connect to the database and get the connection and cursor
connection, cursor = connect_to_database()
    
# inserting miscellaneous data, fetched results, prediction and recommendation into user_data table
def insert_data(sec_token,ip_add,host_name,dev_user,os_name_ver,latlong,city,state,country,act_name,act_mail,act_mob,name,email,res_score,timestamp,no_of_pages,reco_field,cand_level,skills,recommended_skills,courses,pdf_name):
    DB_table_name = 'user_data'
    
    # Check if a record with the same email already exists
    check_sql = "SELECT ID FROM " + DB_table_name + " WHERE act_mail = %s"
    cursor.execute(check_sql, (act_mail,))
    existing_record = cursor.fetchone()
    
    if existing_record:
        # Update the existing record
        update_sql = f"UPDATE {DB_table_name} SET sec_token = %s, ip_add = %s, host_name = %s, dev_user = %s, os_name_ver = %s, latlong = %s, city = %s, state = %s, country = %s, act_name = %s, act_mob = %s, name = %s, email_id = %s, resume_score = %s, Timestamp = %s, Page_no = %s, Predicted_Field = %s, User_level = %s, Actual_skills = %s, Recommended_skills = %s, Recommended_courses = %s, pdf_name = %s WHERE ID = %s"
        update_values = (str(sec_token), str(ip_add), host_name, dev_user, os_name_ver, str(latlong), city, state, country, act_name, act_mob, name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, str(skills), str(recommended_skills), str(courses), pdf_name, existing_record[0])
        
        cursor.execute(update_sql, update_values)
        connection.commit()
    else:
        insert_sql = "insert into " + DB_table_name + """
        values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        rec_values = (str(sec_token),str(ip_add),host_name,dev_user,os_name_ver,str(latlong),city,state,country,act_name,act_mail,act_mob,name,email,str(res_score),timestamp,str(no_of_pages),reco_field,cand_level,skills,recommended_skills,courses,pdf_name)
        cursor.execute(insert_sql, rec_values)
        connection.commit()

    # inserting feedback data into user_feedback table
def insertf_data(feed_name,feed_email,feed_score,comments,Timestamp):
    DBf_table_name = 'user_feedback'
    insertfeed_sql = "insert into " + DBf_table_name + """
    values (0,%s,%s,%s,%s,%s)"""
    rec_values = (feed_name, feed_email, feed_score, comments, Timestamp)
    cursor.execute(insertfeed_sql, rec_values)
    connection.commit()

def run():

     # Check if the connection and cursor are valid
    if connection and cursor:
        try:
            st.title("SkillMatch Resume Analyzer App")
            st.sidebar.markdown("# Select User")
            activities = ["Applicant", "Admin", "Feedback", "About"]
            choice = st.sidebar.selectbox("Select among the given options:", activities)
            link = '<b>Built with 🤍 by <a href="https://github.com/allonekings" style="text-decoration: none; color: #008080;">Elisha Rukovo</a></b>'
            st.sidebar.markdown(link, unsafe_allow_html=True)
            st.sidebar.markdown('''
                <!-- site visitors -->

                <div id="sfc88au2e9z74mpp8nhcy5up6qj41k5lwha"></div>
                <script type="text/javascript" src="https://counter4.optistats.ovh/private/counter.js?c=88au2e9z74mpp8nhcy5up6qj41k5lwha&down=async" async></script>

                <noscript>
                    <a href="https://www.freecounterstat.com" title="website counter">
                        <img "https://counter4.optistats.ovh/private/freecounterstat.php?c=88au2e9z74mpp8nhcy5up6qj41k5lwha" border="0" title="website counter" alt="website counter">
                        </a>
                </noscript>

                <p>Visitors <img src="https://counter4.optistats.ovh/private/freecounterstat.php?c=88au2e9z74mpp8nhcy5up6qj41k5lwha" title="Free Counter" Alt="web counter" width="60px"  border="0" /></p>

            ''', unsafe_allow_html=True)
            gif_path = './Logo/SRAA_Logo.gif'

            # Display the GIF using st.image
            st.image(gif_path, use_column_width=True)

            db_sql = """CREATE DATABASE IF NOT EXISTS freedb_skillmatch;"""
            cursor.execute(db_sql)

            connection.select_db("freedb_skillmatch")
            # Create table user_data and user_feedback
            DB_table_name = 'user_data'
            table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                            (ID INT NOT NULL AUTO_INCREMENT,
                            sec_token varchar(20) NOT NULL,
                            ip_add varchar(50) NULL,
                            host_name varchar(50) NULL,
                            dev_user varchar(50) NULL,
                            os_name_ver varchar(50) NULL,
                            latlong varchar(50) NULL,
                            city varchar(50) NULL,
                            state varchar(50) NULL,
                            country varchar(50) NULL,
                            act_name varchar(50) NOT NULL,
                            act_mail varchar(50) NOT NULL UNIQUE,
                            act_mob varchar(20) NOT NULL,
                            Name varchar(500) NOT NULL,
                            Email_ID VARCHAR(500) NOT NULL,
                            resume_score VARCHAR(8) NOT NULL,
                            Timestamp VARCHAR(50) NOT NULL,
                            Page_no VARCHAR(5) NOT NULL,
                            Predicted_Field BLOB NOT NULL,
                            User_level BLOB NOT NULL,
                            Actual_skills BLOB NOT NULL,
                            Recommended_skills BLOB NOT NULL,
                            Recommended_courses BLOB NOT NULL,
                            pdf_name varchar(50) NOT NULL,
                            PRIMARY KEY (ID)
                            );
                        """
            cursor.execute(table_sql)
            DBf_table_name = 'user_feedback'
            tablef_sql = "CREATE TABLE IF NOT EXISTS " + DBf_table_name + """
                            (ID INT NOT NULL AUTO_INCREMENT,
                                feed_name varchar(50) NOT NULL,
                                feed_email VARCHAR(50) NOT NULL,
                                feed_score VARCHAR(5) NOT NULL,
                                comments VARCHAR(100) NULL,
                                Timestamp VARCHAR(50) NOT NULL,
                                PRIMARY KEY (ID)
                            );
                        """
            cursor.execute(tablef_sql)
            
            if choice == 'Applicant':
                # Collecting User Information
                st.subheader("User Information")
                col1, col2 = st.columns(2)
                with col1:
                    act_name = st.text_input('Name*')
                    act_mail = st.text_input('Mail*')
                    act_mob  = st.text_input('Mobile Number*')
                with col2:
                    city = st.text_input('City*')
                    state = st.text_input('State/Province*')
                    country = st.text_input('Country*')
                
                st.subheader("Additional Information")
                # Collecting additional information
                dev_user = st.text_input('Device User* eg. raphaell')
                
                st.subheader("OS Information")
                # OS and version selection
                os_options = ['Select', 'Windows', 'macOS', 'Linux', 'Android', 'iOS']
                os_name = st.selectbox('OS Name*', os_options)
                
                if os_name != 'Select':
                    if os_name == 'Windows':
                        os_version = st.selectbox('OS Version*', ['Select', '7', '8', '10', '11'])
                    elif os_name == 'macOS':
                        os_version = st.selectbox('OS Version*', ['Select', 'Big Sur', 'Monterey', 'Ventura'])
                    elif os_name == 'Linux':
                        os_version = st.selectbox('OS Version*', ['Select', 'Ubuntu', 'Fedora', 'Arch', 'Debian'])
                    elif os_name == 'Android':
                        os_version = st.selectbox('OS Version*', ['Select', '8', '9', '10', '11', '12'])
                    elif os_name == 'iOS':
                        os_version = st.selectbox('OS Version*', ['Select', '14', '15', '16'])
                else:
                    os_version = 'Select'
                
                # Combine OS name and version
                os_name_ver = f"{os_name} {os_version}" if os_name != 'Select' and os_version != 'Select' else 'Select'

                # Display collected information in an expander
                with st.expander("Your Provided Info"):
                    st.write('### Collected Information')
                    st.write(f'Name: {act_name}')
                    st.write(f'Mail: {act_mail}')
                    st.write(f'Mobile Number: {act_mob}')
                    st.write(f'City: {city}')
                    st.write(f'State/Province: {state}')
                    st.write(f'Country: {country}')
                    st.write(f'Secure Token: {secrets.token_urlsafe(12)}')
                    st.write(f'Device User: {dev_user}')
                    st.write(f'OS Name and Version: {os_name_ver}')

                # Validate required fields
                required_fields_filled = all([
                    act_name, act_mail, act_mob, 
                    city, state, country, 
                    dev_user, os_name != 'Select', os_version != 'Select'
                ])
                email_valid = is_valid_email(act_mail)
                mobile_valid = is_valid_mobile(act_mob)
                
                # Provide feedback on invalid inputs
                if required_fields_filled:
                    if not email_valid:
                        st.error("Please enter a valid email address.")
                    if not mobile_valid:
                        st.warning("Please enter a valid mobile number.")
                    else:
                        st.warning("Please fill in all required fields (Name, Mail, Mobile Number, City, State, Country, Device User, OS Name and Version).")
                
                
                        st.success("All inputs are valid. You can proceed with resume upload.")
                        # Upload Resume
                        st.markdown('''<h5 style='text-align: left; color: #008080;'> Upload Your Resume, And Get Smart Recommendations</h5>''',unsafe_allow_html=True)
                        
                        ## file upload in pdf format
                        pdf_file = st.file_uploader("Choose your Resume in Pdf format", type=["pdf"])
                        if pdf_file is not None:
                            with st.spinner('Hang On While We Cook Magic For You...'):
                                time.sleep(4)
    
                            ### saving the uploaded resume to folder
                            save_image_path = './Uploaded_CVs/'+pdf_file.name
                            pdf_name = pdf_file.name
                            with open(save_image_path, "wb") as f:
                                f.write(pdf_file.getbuffer())
    
                            with st.expander("Your Pdf"):
                                show_pdf(save_image_path)
    
                            ### parsing and extracting whole resume
                            resume_data = ResumeParser(save_image_path).get_extracted_data()
                            if resume_data:
    
                                ## Get the whole resume data into resume_text
                                resume_text = pdf_reader(save_image_path)
                                
                                st.header("**Resume Analysis**")
                                st.success("Hello " + resume_data['name'])
                                st.subheader("**Your Basic info**")
                                try:
                                    st.text('Name: ' + resume_data['name'])
                                    st.text('Email: ' + resume_data['email'])
                                    st.text('Contact: ' + resume_data['mobile_number'])
                                    st.text('Degree: '+str(resume_data['degree']))
                                    st.text('Resume pages: ' + str(resume_data['no_of_pages']))
                                except:
                                    pass
                                ## Predicting Candidate Experience Level
                                ### Trying with different possibilities
                                cand_level = ''
                                if resume_data['no_of_pages'] < 1:
                                    cand_level = "NA"
                                    st.markdown( '''<h4 style='text-align: left; color: #d73b5c;'>You are at Fresher level!</h4>''',unsafe_allow_html=True)
    
                                #### if internship then intermediate level
                                elif 'INTERNSHIP' in resume_text:
                                    cand_level = "Intermediate"
                                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',unsafe_allow_html=True)
                                elif 'INTERNSHIPS' in resume_text:
                                    cand_level = "Intermediate"
                                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',unsafe_allow_html=True)
                                elif 'Internship' in resume_text:
                                    cand_level = "Intermediate"
                                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',unsafe_allow_html=True)
                                elif 'Internships' in resume_text:
                                    cand_level = "Intermediate"
                                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',unsafe_allow_html=True)
    
                                #### if Work Experience/Experience then Experience level
                                elif 'EXPERIENCE' in resume_text:
                                    cand_level = "Experienced"
                                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',unsafe_allow_html=True)
                                elif 'WORK EXPERIENCE' in resume_text:
                                    cand_level = "Experienced"
                                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',unsafe_allow_html=True)
                                elif 'Experience' in resume_text:
                                    cand_level = "Experienced"
                                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',unsafe_allow_html=True)
                                elif 'Work Experience' in resume_text:
                                    cand_level = "Experienced"
                                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',unsafe_allow_html=True)
                                else:
                                    cand_level = "Fresher"
                                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at Fresher level!!''',unsafe_allow_html=True)
                                    
                                st.subheader("**Skills Recommendation💡**")
                                keywords = st_tags(label='### Skills that you have',
                                                text='See our skills recommendation',
                                                value=resume_data['skills'], key='1')
    
                                ### Keywords for Recommendations
                                ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask', 'streamlit']
                                web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress', 'javascript', 'angular js', 'c#', 'flask']
                                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                                ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                                uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes', 'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator', 'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro', 'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp', 'user research', 'user experience']
                                n_any = ['english','communication','writing', 'microsoft office', 'leadership','customer management', 'social media']
    
                                ### Skill Recommendations Starts
                                recommended_skills = []
                                reco_field = ''
                                rec_course = ''
    
                                ### condition starts to check skills from keywords and predict field
                                for i in resume_data['skills']:
                                    
                                    #### Data science recommendation
                                    if i.lower() in ds_keyword:
                                        reco_field = 'Data Scientist'
                                        st.success("** Our analysis says you are looking for Data Science Jobs.**")
                                        recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling', 'Data Mining', 'Clustering & Classification', 'Data Analytics', 'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras', 'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', "Flask", 'Streamlit']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                                    text='Recommended skills generated from System',
                                                                    value=recommended_skills, key='2')
                                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding these skills to your resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                                        rec_course = course_recommender(ds_course)
                                        break
                                    elif i.lower() in web_keyword:
                                        reco_field = 'Web Developer'
                                        st.success("** Our analysis says you are looking for Web Development Jobs **")
                                        recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento', 'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                                    text='Recommended skills generated from System',
                                                                    value=recommended_skills, key='3')
                                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding these skills to your resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                                        rec_course = course_recommender(web_course)
                                        break
                                    elif i.lower() in android_keyword:
                                        reco_field = 'Android Developer'
                                        st.success("** Our analysis says you are looking for Android App Development Jobs **")
                                        recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java', 'Kivy', 'GIT', 'SDK', 'SQLite']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                                    text='Recommended skills generated from System',
                                                                    value=recommended_skills, key='4')
                                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                                        rec_course = course_recommender(android_course)
                                        break
                                    elif i.lower() in ios_keyword:
                                        reco_field = 'IOS Developer'
                                        st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                                        recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode', 'Objective-C', 'SQLite', 'Plist', 'StoreKit', "UI-Kit", 'AV Foundation', 'Auto-Layout']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                                    text='Recommended skills generated from System',
                                                                    value=recommended_skills, key='5')
                                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding these skills to your resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                                        rec_course = course_recommender(ios_course)
                                        break
                                    elif i.lower() in uiux_keyword:
                                        reco_field = 'UI-UX Developer'
                                        st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                                        recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq', 'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing', 'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe', 'User Research']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                                    text='Recommended skills generated from System',
                                                                    value=recommended_skills, key='6')
                                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Adding these skills to your resume will boost🚀 the chances of getting a Job💼</h4>''', unsafe_allow_html=True)
                                        rec_course = course_recommender(uiux_course)
                                        break
                                    #### For Not Any Recommendations
                                    elif i.lower() in n_any:
                                        print(i.lower())
                                        reco_field = 'NA'
                                        st.warning("** Currently our tool only predicts and recommends for Data Science, Web, Android, IOS and UI/UX Development**")
                                        recommended_skills = ['No Recommendations']
                                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                        text='Currently No Recommendations',value=recommended_skills,key = '6')
                                        st.markdown('''<h5 style='text-align: left; color: #092851;'>Maybe Available in Future Updates</h5>''',unsafe_allow_html=True)
                                        # course recommendation
                                        rec_course = "Sorry! Not Available for this Field"
                                        break
                                    
                                    else:
                                        reco_field = 'Others'
                                
                                recommended_skills = [x.lower() for x in recommended_skills]
                                rec_course = ', '.join(rec_course)
    
                                ## Insert into table
                                ts = time.time()
                                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                                timestamp = str(cur_date + '_' + cur_time)
    
                                with st.expander("See How to Improve your Resume"):
                                    ### Resume writing recommendation
                                    st.subheader("**CV Writing Tips & Ideas💡**")
                                    resume_score = 0
    
                                    ### Predicting Whether these key points are added to the resume
                                    if 'Objective' or 'Summary' in resume_text:
                                        resume_score = resume_score + 5
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective/Summary</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add your career objective, it will give your career intension to the Recruiters.</h4>''',unsafe_allow_html=True)
    
                                    if 'Declaration' in resume_text:
                                        resume_score = resume_score + 2
                                        st.markdown(
                                            '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Delcaration✍/h4>''',
                                            unsafe_allow_html=True)
                                    else:
                                        st.markdown(
                                            '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''',
                                            unsafe_allow_html=True)
    
                                    if 'Education' or 'School' or 'College'  in resume_text:
                                        resume_score = resume_score + 10
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Education Details</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Education. It will give Your Qualification level to the recruiter</h4>''',unsafe_allow_html=True)
    
                                    if 'EXPERIENCE' in resume_text:
                                        resume_score = resume_score + 20
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Experience</h4>''',unsafe_allow_html=True)
                                    elif 'Experience' in resume_text:
                                        resume_score = resume_score + 20
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Experience</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Experience. It will help you to stand out from crowd</h4>''',unsafe_allow_html=True)
    
                                    if 'INTERNSHIPS'  in resume_text:
                                        resume_score = resume_score + 8
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                                    elif 'INTERNSHIP'  in resume_text:
                                        resume_score = resume_score + 8
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                                    elif 'Internships'  in resume_text:
                                        resume_score = resume_score + 8
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                                    elif 'Internship'  in resume_text:
                                        resume_score = resume_score + 8
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Internships. It will help you to stand out from crowd</h4>''',unsafe_allow_html=True)
    
                                    if 'SKILLS'  in resume_text:
                                        resume_score = resume_score + 15
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                                    elif 'SKILL'  in resume_text:
                                        resume_score = resume_score + 15
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                                    elif 'Skills'  in resume_text:
                                        resume_score = resume_score + 15
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                                    elif 'Skill'  in resume_text:
                                        resume_score = resume_score + 15
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Skills. It will help you a lot</h4>''',unsafe_allow_html=True)
    
                                    if 'HOBBIES' in resume_text:
                                        resume_score = resume_score + 3
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies</h4>''',unsafe_allow_html=True)
                                    elif 'Hobbies' in resume_text:
                                        resume_score = resume_score + 3
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Hobbies. It will show your personality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',unsafe_allow_html=True)
    
                                    if 'INTERESTS'in resume_text:
                                        resume_score = resume_score + 3
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Interest</h4>''',unsafe_allow_html=True)
                                    elif 'Interests'in resume_text:
                                        resume_score = resume_score + 3
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Interest</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Interest. It will show your interest other that job.</h4>''',unsafe_allow_html=True)
    
                                    if 'ACHIEVEMENTS' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements </h4>''',unsafe_allow_html=True)
                                    elif 'Achievements' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements </h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Achievements. It will show that you are capable for the required position.</h4>''',unsafe_allow_html=True)
    
                                    if 'CERTIFICATIONS' in resume_text:
                                        resume_score = resume_score + 10
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                                    elif 'Certifications' in resume_text:
                                        resume_score = resume_score + 10
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                                    elif 'Certification' in resume_text:
                                        resume_score = resume_score + 10
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Certifications. It will show that you have done some specialization for the required position.</h4>''',unsafe_allow_html=True)
    
                                    if 'PROJECTS' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                                    elif 'PROJECT' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                                    elif 'Projects' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                                    elif 'Project' in resume_text:
                                        resume_score = resume_score + 12
                                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                                    else:
                                        st.markdown('''<h5 style='text-align: left; color: #fabc10;'>[-] Please add Projects. It will show that you have done work related the required position or not.</h4>''',unsafe_allow_html=True)
    
                                st.subheader("**Resume Score📝**")
                                st.markdown(
                                    """
                                    <style>
                                        .stProgress > div > div > div > div {
                                            background-color: #d73b5c;
                                        }
                                    </style>""",
                                    unsafe_allow_html=True,
                                )
                                my_bar = st.progress(0)
                                score = 0
                                for percent_complete in range(resume_score):
                                    score += 1
                                    time.sleep(0.1)
                                    my_bar.progress(percent_complete + 1)
                                st.success('** Your CV Writing Score: ' + str(score) + '**')
                                st.warning(
                                    "** Note: This score is calculated based on the content that you have provided in your CV. **")
    
                                with st.expander("Watch Tips on Writing a beter Resume"):
                                    ## Resume writing video
                                    st.header("**Bonus Video for CV Writing Tips💡**")
                                    resume_vid = random.choice(resume_videos)
                                    res_vid_title = fetch_yt_video(resume_vid)
                                    st.subheader("✅ **" + res_vid_title + "**")
                                    st.video(resume_vid)
    
                                with st.expander("Watch to get ready for Interview"):
                                    ## Interview Preparation Video
                                    st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                                    interview_vid = random.choice(interview_videos)
                                    int_vid_title = fetch_yt_video(interview_vid)
                                    st.subheader("✅ **" + int_vid_title + "**")
                                    st.video(interview_vid)
    
                                connection.commit()
                                
                                st.header("**Download your Analysis Report**")
                                # Create DataFrame from dictionary with the index as the row labels
                                df_report = pd.DataFrame.from_dict(resume_data, orient='index')
                                df_report.reset_index(inplace=True)
                                df_report.columns = ['index', 'Details']
                                st.dataframe(df_report, width=800)
                                st.write(get_table_download_link(df_report, 'resume_analysis_report.csv', 'Download Report'),
                                        unsafe_allow_html=True)
                                st.write(" ")
                                st.balloons()
                                # Display the prompt to the user
                                st.write("""
                                    Please review all the information you have entered. If everything looks good and you are ready to proceed, click on 'Submit Resume'.
                                    Once submitted, your resume will be added to our database, and you will also receive a list of other job opportunities tailored to your profile.
                                    Make sure all details are correct before submitting.
                                """)
                                if st.button('Submit'):
                                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    insert_data(str(sec_token), str(ip_add), (host_name), (dev_user), (os_name_ver), (latlong), (city), (state), (country), (act_name), (act_mail), (act_mob), resume_data['name'], resume_data['email'], str(resume_score), timestamp,
                                                str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']),
                                                str(recommended_skills), str(rec_course), pdf_name)
                                    st.success("Your resume has been submitted successfully! You will receive job listings shortly.")
                                    with st.spinner('Hang On While We Cook Magic For You...'):
                                        time.sleep(4)
                                        
                                    st.subheader("**Job Listings📄**")
                                    
                                    # Pause for 5 seconds before retrying the request
                                    time.sleep(5)
    
                                    # API configuration
                                    url = RAPID_URL
                                    querystring = {
                                        "query": reco_field,
                                        #"Zimbabwe"
                                        "location": country,
                                        "distance": "1.0",
                                        "language": "en_GB",
                                        "remoteOnly": "false",
                                        "datePosted": "month",
                                        "employmentTypes": "fulltime;parttime;intern;contractor",
                                        "index": "0"
                                    }
                                    headers = {
                                        "X-RapidAPI-Key": X_RapidAPI_Key,
                                        "X-RapidAPI-Host": X_RapidAPI_Host
                                    }
    
                                    # Fetch data from the API
                                    response = requests.get(url, headers=headers, params=querystring)
    
                                    # Check if response is successful
                                    if response.status_code == 200:
                                        dataResponse = response.json()
                                        job_listings = dataResponse.get('jobs', [])
    
                                        # If job listings are found
                                        if job_listings:
                                            job_data = []
                                            for job in job_listings:
                                                provider_names = []
                                                provider_urls = []
                                                for provider in job['jobProviders']:
                                                    provider_names.append(provider['jobProvider'])
                                                    provider_urls.append(provider['url'])
    
                                                job_data.append({
                                                    'title': job['title'],
                                                    'company': job['company'],
                                                    'location': job['location'],
                                                    'description': job['description'],
                                                    'datePosted': job['datePosted'],
                                                    'employmentType': job['employmentType'],
                                                    'providerName': ', '.join(provider_names),
                                                    'providerUrl': ', '.join(provider_urls)
                                                })
    
                                            # Create DataFrame
                                            df = pd.DataFrame(job_data)
                                            columns_to_display = ['title', 'company', 'location', 'description', 'datePosted', 'employmentType', 'providerName', 'providerUrl']
                                            df = df[columns_to_display]
    
                                            # Display job listings
                                            for index, row in df.iterrows():
                                                st.subheader(f"Job {index + 1}: {row['title']} - {row['company']}")
                                                st.write(f"**Location:** {row['location']}")
                                                st.write(f"**Posted:** {row['datePosted']}")
                                                st.write(f"**Employment Type:** {row['employmentType']}")
                                                st.subheader("Description:")
                                                description = row['description']
                                                description_lines = description.split('\n')
                                                current_subheading = ""
                                                for line in description_lines:
                                                    if line.startswith("**"):
                                                        if current_subheading != "":
                                                            st.write("")
                                                        current_subheading = line
                                                        st.write(f"**{current_subheading}**")
                                                    else:
                                                        st.write(f"  {line}")
                                                st.markdown(f"[Provider URL for Job {index + 1}]({row['providerUrl']})",)
                                                st.write("---")
                                            ## On Successful Result
                                            st.balloons()
                                        else:
                                            st.error("No job listings found from your Field. Please try again later or check back for updates.")
                                    else:
                                        st.error(f"Error: {response.status_code}")
                            else:
                                st.error("No data found in resume.")
                else:
                    st.warning("Please fill in all required fields (Name, Mail, Mobile Number) before uploading your resume.")
            
            ###### CODE FOR FEEDBACK SIDE ######
            elif choice == 'Feedback':

                # timestamp
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date+'_'+cur_time)

                # Feedback Form
                with st.form("my_form"):
                    st.write("Feedback form")
                    feed_name = st.text_input('Name')
                    feed_email = st.text_input('Email')
                    feed_score = st.slider('Rate Us From 1 - 5', 1, 5)
                    comments = st.text_input('Comments')
                    Timestamp = timestamp
                    submitted = st.form_submit_button("Submit")
                    if submitted:
                        ## Calling insertf_data to add dat into user feedback
                        insertf_data(feed_name,feed_email,feed_score,comments,Timestamp)
                        ## Success Message
                        st.success("Thanks! Your Feedback was recorded.")
                        ## On Successful Submit
                        st.balloons()


                # Fetch feedback data from user_feedback(table) and convert it into dataframe
                cursor.execute('''SELECT * from user_feedback''')
                feed_data = cursor.fetchall()
                feed_df = pd.DataFrame(feed_data, columns=['ID', 'Name', 'Email', 'Feedback Score', 'Comments', 'Timestamp'])


                # plotting pie chart for user ratings
                st.subheader("User Ratings")
                fig = px.pie(feed_df, names='Feedback Score', title="Chart of User Rating Score From 1 - 5 🤗")
                st.plotly_chart(fig, use_container_width=True)


                #  Fetching Comment History
                cursor.execute('select feed_name, comments from user_feedback')
                plfeed_cmt_data = cursor.fetchall()

                st.subheader("**User Comment's**")
                dff = pd.DataFrame(plfeed_cmt_data, columns=['User', 'Comment'])
                st.dataframe(dff, width=1000)


            ###### CODE FOR ABOUT PAGE ######
            elif choice == 'About':

                st.subheader("**About The Tool - AI RESUME ANALYZER**")

                st.markdown('''

                <p align='justify'>
                    A tool which parses information from a resume using natural language processing and finds the keywords, cluster them onto sectors based on their keywords. And lastly show recommendations, predictions, analytics to the applicant based on keyword matching.
                </p>

                <p align="justify">
                    <b>How to use it: -</b> <br/><br/>
                    <b>User -</b> <br/>
                    In the Side Bar choose yourself as user and fill the required fields and upload your resume in pdf format.<br/>
                    Just sit back and relax our tool will do the magic on it's own.<br/><br/>
                    <b>Feedback -</b> <br/>
                    A place where user can suggest some feedback about the tool.<br/><br/>
                    <b>Admin -</b> <br/>
                    For login use username and as password set in enviroment variables.<br/>
                    It will load all the required stuffs and perform analysis.
                </p><br/><br/>

                <p align="justify">
                    Built with 🤍 by
                    <a href="https://github.com/allonekings" style="text-decoration: none; color: #008080;">Elisha Rukovo</a> through
                    <a href="https://ww5.msu.ac.zw/" style="text-decoration: none; color: #008080;">Midlands State University --(Dissertation Project)</a>
                </p>

                ''',unsafe_allow_html=True)


            ###### CODE FOR ADMIN SIDE (ADMIN) ######
            elif choice == 'Admin':
                st.markdown("## Admin Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type='password')
                if st.checkbox("Login"):
                    if username ==ADMIN_USERNAME and password == ADMIN_PASSWORD:
                        st.sidebar.success('Logged in as admin')
                        
                        # Fetch miscellaneous data from user_data(table) and convert it into dataframe
                        cursor.execute('''SELECT ID, ip_add, resume_score, convert(Predicted_Field using utf8), convert(User_level using utf8), city, state, country from user_data''')
                        datanalys = cursor.fetchall()
                        plot_data = pd.DataFrame(datanalys, columns=['Idt', 'IP_add', 'resume_score', 'Predicted_Field', 'User_Level', 'City', 'State', 'Country'])

                        # Check if data is retrieved
                        if not plot_data.empty:
                            # Fetch user data from user_data(table) and convert it into dataframe
                            cursor.execute('''SELECT ID, sec_token, ip_add, act_name, act_mail, act_mob, convert(Predicted_Field using utf8), Timestamp, Name, Email_ID, resume_score, Page_no, pdf_name, convert(User_level using utf8), convert(Actual_skills using utf8), convert(Recommended_skills using utf8), convert(Recommended_courses using utf8), city, state, country, latlong, os_name_ver, host_name, dev_user from user_data''')
                            data = cursor.fetchall()
                            df = pd.DataFrame(data, columns=['ID', 'Token', 'IP Address', 'Name', 'Mail', 'Mobile Number', 'Predicted Field', 'Timestamp', 'Predicted Name', 'Predicted Mail', 'Resume Score', 'Total Page',  'File Name', 'User Level', 'Actual Skills', 'Recommended Skills', 'Recommended Course', 'City', 'State', 'Country', 'Lat Long', 'Server OS', 'Server Name', 'Server User'])

                            # Fetch feedback data from user_feedback(table) and convert it into dataframe
                            cursor.execute('''SELECT * from user_feedback''')
                            feed_data = cursor.fetchall()
                            feed_df = pd.DataFrame(feed_data, columns=['ID', 'Name', 'Email', 'Feedback Score', 'Comments', 'Timestamp'])

                            # Analyzing All the Data's in pie charts
                            st.subheader("Analytics")
                            st.markdown("### No of Resumes Uploaded")
                            st.markdown(f"<h1 style='font-size: 72px; color: #1ed760;'>{len(plot_data)}</h1>", unsafe_allow_html=True)
                            
                            tab1, tab2, tab3 = st.tabs(["Database", "Analytics", "Usage"])

                            with tab1:
                                tab1, tab2a = st.tabs(["User Data", "Feedback Data"])
                                with tab1:
                                    st.subheader("Database")
                                    st.header("**User Data**")
                                    st.dataframe(df)
                                    st.markdown(get_table_download_link(df, 'user_data.csv', 'Download user_data as CSV'), unsafe_allow_html=True)

                                with tab2a:
                                    st.header("**User's Feedback Data**")
                                    st.dataframe(feed_df)
                                    # st.markdown(get_table_download_link(feed_df, 'feedback_data.csv', 'Download feedback_data as CSV'), unsafe_allow_html=True)

                            with tab2:
                                tab1, tab2, tab3b, tab4 = st.tabs(["User Level", "Fields Applied For", "User Ratings", "Resume Score"])
                                # Pie chart for user level
                                with tab1:
                                    st.subheader("Level of candidates")
                                    fig = px.pie(plot_data, names='User_Level', title='Level of Candidates')
                                    st.plotly_chart(fig, use_container_width=True)

                                # Pie chart for fields applied for
                                with tab2:
                                    st.subheader("Fields Applied for")
                                    fig = px.pie(plot_data, names='Predicted_Field', title='Fields Applied for')
                                    st.plotly_chart(fig, use_container_width=True)

                                # Pie chart for user ratings
                                with tab3b:
                                    st.subheader("User Ratings")
                                    fig = px.pie(feed_df, names='Feedback Score', title="Chart of User Rating Score From 1 - 5 🤗")
                                    st.plotly_chart(fig, use_container_width=True)

                                # Pie chart for resume score
                                with tab4:
                                    st.subheader("Resume Score")
                                    fig = px.pie(plot_data, names='resume_score', title='From 1 to 100 💯')
                                    st.plotly_chart(fig, use_container_width=True)


                            with tab3:
                                tab1, tab2, tab3, tab4, tab5 = st.tabs(["App Use Count", "Usage Based On City", "Usage Based on State", "Usage Based on Country", "Recommended skills"])
                                
                                with tab1:
                                    # Pie chart for App Use Count
                                    st.subheader("App Use Count")
                                    fig = px.pie(values=df['IP Address'].value_counts(), names=df['IP Address'].unique(), title='Usage Based On IP Address 👥', color_discrete_sequence=px.colors.sequential.matter_r)
                                    st.plotly_chart(fig, use_container_width=True)

                                with tab2:
                                    # Pie chart for Usage Based On City
                                    st.subheader("Usage Based On City")
                                    fig = px.pie(values=df['City'].value_counts(), names=df['City'].unique(), title='Usage Based On City 🌆', color_discrete_sequence=px.colors.sequential.Jet)
                                    st.plotly_chart(fig, use_container_width=True)

                                with tab3:
                                    # Pie chart for Usage Based On State
                                    st.subheader("Usage Based On State")
                                    fig = px.pie(values=df['State'].value_counts(), names=df['State'].unique(), title='Usage Based on State 🚉', color_discrete_sequence=px.colors.sequential.PuBu_r)
                                    st.plotly_chart(fig, use_container_width=True)

                                with tab4:
                                    # Pie chart for Usage Based on Country
                                    st.subheader("Usage Based on Country")
                                    fig = px.pie(values=df['Country'].value_counts(), names=df['Country'].unique(), title='Usage Based on Country 🌏', color_discrete_sequence=px.colors.sequential.Purpor_r)
                                    st.plotly_chart(fig, use_container_width=True)

                                with tab5:
                                    # Word cloud for Recommended Skills
                                    st.subheader("Skills Recommendation")
                                    skills_str = ' '.join(df['Recommended Skills'].dropna())
                                    if skills_str:
                                        from wordcloud import WordCloud, STOPWORDS
                                        import matplotlib.pyplot as plt
                                        wordcloud = WordCloud(width=800, height=800, background_color='white', stopwords=set(STOPWORDS), min_font_size=10).generate(skills_str)
                                        st.image(wordcloud.to_array())
                                    else:
                                        st.write("No skills recommended.")
                                        st.warning("Check to see if any resume has been uploaded first.")

                        else:
                            st.error("No data found in user_data table.")
                    else:
                        st.sidebar.warning("Incorrect Username/Password")
        except Exception as e:
            # Handle database operation errors
            st.error(f"Error executing SQL query: {e}")
        finally:
            cursor.close()  # Close the cursor
            connection.close()  # Close the connection
    else:
        # Handle the case when connection or cursor is None
        st.warning('Could not connect to the database. Please try again later.')

                    
run()
