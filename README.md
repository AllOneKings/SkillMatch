# ⚙️ AI Smart Resume Analyzer (Dissertation)
![Python](https://img.shields.io/badge/python-3.10-blue)
![spaCy](https://img.shields.io/badge/spaCy-2.3.9-green)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An intelligent system that uses artificial intelligence and natural language processing techniques to swiftly and accurately assess and evaluate resumes. It automatically extracts pertinent information, assesses qualifications, and delivers insights based on job needs, assisting recruiters and hiring managers.

## 💁‍♂️ For Assistance
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://linkedin.com/in/elisharukovo)
[![Email](https://img.shields.io/badge/Email-elisharukovo94%40gmail.com-red?style=flat&logo=gmail&logoColor=white)](mailto:elisharukovo94@gmail.com)

## 🌟 Features
- User & Admin Section
- Resume Score
- Career Recommendations
- Resume Writing Tips Suggestions
- Courses Recommendations
- Skills Recommendations
- YouTube Video Recommendations
- Job Listings

## 🛠️ Technologies Used
| Frontend       | Model      | Database |
|----------------|------------|---------|
| Python + Streamlit | KNN Classifier | MySQL |

## 👩‍💻 Source
- Extracting user information from resumes: [PyResparser](https://omkarpathak.in/pyresparser/)  
- Extracting resume PDF into text: [PDFMiner](https://pypi.org/project/pdfminer/)

## 💻 Screenshots
| User Side | Admin Side |
|-----------|------------|
| ![Home Page](/applicant.jpg) | ![Admin Page](/admin.jpg) |

## 🚀 Setup Instructions
1. Clone the repository:
```bash
git clone https://github.com/elisharukovo/SkillMatch.git
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

4. Start XAMPP or any other control panel; turn on Apache & MySQL.  

5. Admin credentials:
```
username: raphaellG
password: admin@123
```

6. `Courses.py` contains courses and YouTube links.  
7. Uploaded resumes are stored in the `Uploaded_Resumes` folder.  

## 🤝 Contributing
- Suggest improvements to AI scoring algorithms  
- Enhance UI/UX  
- Add new resume parsing features  
- Improve recommendation system  

## 📅 Roadmap
- Extend AI models for better recommendations  
- Integrate LinkedIn scraping  
- Mobile-friendly interface  

## 📄 License
MIT License
