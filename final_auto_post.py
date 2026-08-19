import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import re
import urllib.parse
import time
import google.auth.transport.requests
from google.oauth2 import service_account
from google.auth.transport import Request
def notify_google_indexing(url):
    SCOPES = ["https://www.googleapis.com/auth/indexing"]
    ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    try:
        creds = service_account.Credentials.from_service_account_file(
            'indexingKey.json', scopes=SCOPES
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }
        body = {
            "url": url,
            "type": "URL_UPDATED"
        }
        
        response = requests.post(ENDPOINT, headers=headers, json=body)
        if response.status_code == 200:
            print(f"🚀 Google Instant Indexing Success: {url}")
        else:
            print(f"⚠️ Indexing API Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Indexing API Error: {e}")

# --- 1. FIREBASE SETUP ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Connected Successfully!")
except Exception as e:
    print("❌ Firebase Error:", e)
    exit()

GOOGLE_SERVER_URL = "https://script.google.com/macros/s/AKfycbyo025_xgev4ItpdWA6VaycY4nBPLXvPro97qjhJd4U0kFSv5CmqPks64hz96mCxIsk/exec"

def create_slug(title):
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
    return slug.strip('-')

# --- 2. PRECISE DATA EXTRACTION ---
def scrape_inner_details(job_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(job_url, headers=headers, timeout=15)
    except:
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    details = {
        "Important_Dates": [], 
        "Application_Fee": [], 
        "How_To_Apply": [], 
        "FAQs": [], 
        "Important_Links": {}
    }
    
    for cell in soup.find_all(['td', 'div']):
        cell_text = cell.get_text(separator=" ", strip=True).lower()
        
        if ("important date" in cell_text or "application begin" in cell_text) and len(cell_text) < 800:
            if not details["Important_Dates"] and "application fee" not in cell_text:
                lis = cell.find_all('li')
                details["Important_Dates"] = [li.get_text(separator=" ", strip=True) for li in lis] if lis else [l.strip() for l in cell.get_text(separator="\n").split("\n") if l.strip() and "date" not in l.lower()]
                    
        if "application fee" in cell_text and len(cell_text) < 800:
            if not details["Application_Fee"] and "important date" not in cell_text:
                lis = cell.find_all('li')
                details["Application_Fee"] = [li.get_text(separator=" ", strip=True) for li in lis] if lis else [l.strip() for l in cell.get_text(separator="\n").split("\n") if l.strip() and "fee" not in l.lower()]

        if ("how to fill" in cell_text or "how to apply" in cell_text) and len(cell_text) < 1500:
            if not details["How_To_Apply"] and "important date" not in cell_text and "application fee" not in cell_text:
                lis = cell.find_all('li')
                if lis:
                    details["How_To_Apply"] = [li.get_text(separator=" ", strip=True) for li in lis if li.get_text(strip=True)]

    for li in soup.find_all('li'):
        li_text = li.get_text(separator=" ", strip=True)
        li_text = re.sub(r'\s+', ' ', li_text) 
        
        if li_text.lower().startswith('question:') or li_text.lower().startswith('answer:'):
            details["FAQs"].append(li_text)

    for tr in soup.find_all('tr'):
        tr_text = tr.text.lower()
        link_tag = tr.find('a')
        if link_tag and link_tag.get('href'):
            href = link_tag.get('href')
            if 'apply' in tr_text or 'registration' in tr_text:
                details["Important_Links"]["Apply Online"] = href
            elif 'download result' in tr_text or 'result' in tr_text:
                details["Important_Links"]["Download Result"] = href
            elif 'download admit card' in tr_text or 'admit card' in tr_text:
                details["Important_Links"]["Download Admit Card"] = href
            elif 'notification' in tr_text:
                details["Important_Links"]["Download Notification"] = href
            elif 'official website' in tr_text:
                details["Important_Links"]["Official Website"] = href
                
    return details

# --- 3. PREMIUM SEO HTML GENERATOR ---
def generate_seo_html(title, inner_data, category_label):
    html = f"""
    <div class="seo-content" style="padding: 18px; background: #f0f8ff; border-left: 5px solid #2980b9; margin-bottom: 25px; border-radius: 0 8px 8px 0; text-align: justify;">
        <h2 style="color: #2c3e50; font-size: 24px; margin-top: 0; margin-bottom: 15px; font-weight: 800;">{title} - Complete Details & Updates</h2>
        <p style="font-size: 16px; line-height: 1.8; color: #444; margin-bottom: 12px;">Are you looking for the latest updates on <strong>{title}</strong>? You are in the right place! The authorities have recently published the official details for the <strong>{title} ({category_label})</strong>. Candidates who are preparing for this exam must stay updated with the latest news, exam dates, admit card status, and result announcements.</p>
        <p style="font-size: 16px; line-height: 1.8; color: #444; margin-bottom: 0;">In this comprehensive guide by <strong>Student Help Club</strong>, we will walk you through all the crucial details related to the <strong>{title}</strong>. Make sure to read the eligibility criteria, category-wise fee details, and step-by-step application instructions carefully before proceeding to the official website.</p>
    </div>
    """
    
    html += '<div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom: 25px;">'
    if inner_data["Important_Dates"]:
        dates_list = "".join([f"<li style='margin-bottom:8px;'>{d}</li>" for d in inner_data["Important_Dates"]])
        html += f'<div class="info-box" style="flex:1; min-width:300px;"><div class="box-title">Important Dates</div><div class="box-content"><ul>{dates_list}</ul></div></div>'
        
    if inner_data["Application_Fee"]:
        fees_list = "".join([f"<li style='margin-bottom:8px;'>{f}</li>" for f in inner_data["Application_Fee"]])
        html += f'<div class="info-box" style="flex:1; min-width:300px;"><div class="box-title">Application Fee</div><div class="box-content"><ul>{fees_list}</ul></div></div>'
    html += '</div>'
    
    if inner_data["How_To_Apply"]:
        html += f"""
        <div class="seo-content" style="padding: 18px; background: #fdfefe; border-left: 5px solid #e67e22; margin: 30px 0 20px 0; border-radius: 0 8px 8px 0; text-align: justify; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
            <h3 style="color: #d35400; font-size: 21px; margin-top: 0; margin-bottom: 10px; font-weight: 700;">How to Apply / Check Status for {title}</h3>
            <p style="font-size: 16px; line-height: 1.8; color: #444; margin-bottom: 0;">Following the correct procedure is very important to avoid rejection. Below is the step-by-step guide for the <strong>{title}</strong>. Candidates are advised to keep their necessary documents, scanned photographs, and signatures ready before filling out the online form or checking their status.</p>
        </div>
        """
        steps_list = "".join([f"<li style='margin-bottom:10px;'>{step}</li>" for step in inner_data["How_To_Apply"]])
        html += f'<div class="info-box"><div class="box-title" style="background:#e67e22; color:white;">Important Instructions</div><div class="box-content"><ul>{steps_list}</ul></div></div>'

    if inner_data["FAQs"]:
        html += f"""
        <div class="seo-content" style="padding: 18px; background: #fcf3cf; border-left: 5px solid #f1c40f; margin: 30px 0 20px 0; border-radius: 0 8px 8px 0; text-align: justify; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
            <h3 style="color: #b7950b; font-size: 21px; margin-top: 0; margin-bottom: 10px; font-weight: 700;">Important FAQs regarding {title}</h3>
            <p style="font-size: 16px; line-height: 1.8; color: #444; margin-bottom: 0;">Candidates often have several doubts regarding the recruitment process, exam date, syllabus, and admit card release for the <strong>{title}</strong>. Here are some of the most Frequently Asked Questions (FAQs) along with their answers based on the official notification.</p>
        </div>
        """
        html += '<div class="info-box"><div class="box-title" style="background:#8e44ad; color:white;">Frequently Asked Questions (FAQs)</div><div class="box-content" style="padding:20px;">'
        for faq in inner_data["FAQs"]:
            if faq.lower().startswith('question:'):
                clean_q = re.sub(r'(?i)^Question\s*:\s*', '', faq)
                html += f'<div style="margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px dashed #eee;"><b style="color:#d35400; font-size: 17px;">Q. {clean_q}</b><br>'
            elif faq.lower().startswith('answer:'):
                clean_a = re.sub(r'(?i)^Answer\s*:\s*', '', faq)
                html += f'<span style="color:#2c3e50; display: inline-block; margin-top: 8px; font-size: 16px; line-height: 1.6;"><b>Ans:</b> {clean_a}</span></div>'
        html += '</div></div>'
    
    html += f"""
    <div class="seo-content" style="padding: 18px; background: #e8f8f5; border-left: 5px solid #1abc9c; margin: 30px 0 20px 0; border-radius: 0 8px 8px 0; text-align: justify; box-shadow: 0 2px 10px rgba(0,0,0,0.03);">
        <h3 style="color: #16a085; font-size: 21px; margin-top: 0; margin-bottom: 10px; font-weight: 700;">Direct Important Links for {title}</h3>
        <p style="font-size: 16px; line-height: 1.8; color: #444; margin-bottom: 0;">Bookmark this page for future reference! Below we have provided all the direct official links for the <strong>{title}</strong>. You can easily download the official notification, apply online, or view your result directly from the table below without searching anywhere else.</p>
    </div>
    """
    
    link_rows = ""
    for link_name, link_url in inner_data["Important_Links"].items():
        link_rows += f'<tr><td style="padding: 12px;"><b>{link_name}</b></td><td style="padding: 12px;"><a href="{link_url}" target="_blank" style="font-weight:bold;">Click Here</a></td></tr>'
        
    link_rows += '<tr><td style="padding: 12px;">Join Telegram Group</td><td style="padding: 12px;"><a href="https://t.me/studenthelpclub" style="color:#0088cc; font-weight:bold;">Join Now</a></td></tr>'
    link_rows += '<tr><td style="padding: 12px;">Join WhatsApp Channel</td><td style="padding: 12px;"><a href="https://whatsapp.com/channel/0029VbCJ2xI7IUYa1zMB6n1f" style="color:#25d366; font-weight:bold;">Join Now</a></td></tr>'

    html += f'<div class="info-box" style="margin-bottom: 40px;"><div class="box-title" style="background:#27ae60; color:white;">Important Links</div><div class="box-content"><table class="link-table" style="width: 100%; border-collapse: collapse;">{link_rows}</table></div></div>'
    
    return html

# --- 4. HUMAN-LIKE HEADING FINDER (NO IDs USED) ---
def get_correct_container(soup, category_headings):
    for ch in category_headings:
        # Pura exact match check karo pehle
        headings = soup.find_all(string=lambda t: t and t.strip().lower() == ch)
        
        # Agar exact match nahi mila toh partial match
        if not headings:
            headings = soup.find_all(string=lambda t: t and ch in t.lower() and len(t.strip()) < 20)

        for h in headings:
            # Agar heading kisi link me hai ya footer tag me hai toh use turant ignore maro
            if h.find_parent('a') or h.find_parent('footer') or h.find_parent(id=lambda x: x and 'footer' in x.lower()) or h.find_parent(['script', 'style', 'title']):
                continue
                
            parent = h.parent
            while parent and parent.name not in ['body', 'html']:
                links = parent.find_all('a')
                # Asli box me lagbhag 5 se 60 links hote hain
                if 3 < len(links) < 80:
                    return parent
                parent = parent.parent
                
    return None

# --- 5. MASTER AUTOMATION ---
def run_automation():
    print("\n🚀 MASTER AUTOMATION START (Fetching Jobs, Admit Cards, and Results)...")
    url = "https://sarkariresult.com.cm"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print("❌ Website load nahi hui:", e)
        return

    # Ab ID ki zaroorat nahi hai, script strictly headings padhegi
    categories = [
        {"headings": ["latest jobs", "latest job"], "collection": "jobs", "label": "Latest Job"},
        {"headings": ["admit card", "admit cards"], "collection": "admit", "label": "Admit Card"},
        {"headings": ["results", "result"], "collection": "result", "label": "Result"} 
    ]
    
    bad_exact_words = [
        "home", "latest job", "latest jobs", "admit card", "result", "results", 
        "admission", "syllabus", "answer key", "contact us", "sarkari", 
        "sarkariresult", "sarkari result", "sarkari result 2026", 
        "bihar police result", "up police result", "bharat result", 
        "search result", "board result", "all board result"
    ]
    bad_keywords = ["privacy", "disclaimer", "about us", "contact", "terms", "policy", "facebook", "twitter", "youtube", "instagram", "telegram", "whatsapp"]

    for cat in categories:
        print(f"\n==================================================")
        print(f"🔎 Scanning Category: {cat['label'].upper()}")
        print(f"==================================================")
        
        container = get_correct_container(soup, cat["headings"])

        if not container:
            print(f"❌ {cat['label']} ka asli dabba nahi mila. Skipping...")
            continue
            
        all_job_links = container.find_all('a')
        valid_links_processed = 0
        
        for job_link in all_job_links:
            if valid_links_processed >= 10:
                break 
                
            title = job_link.text.strip()
            title_lower = title.lower()
            job_url = job_link.get('href')
            
            if not title or len(title) < 8: 
                continue
                
            if title_lower in bad_exact_words or "sarkari result" in title_lower:
                continue
                
            skip_this_link = False
            for bad_word in bad_keywords:
                if bad_word in title_lower:
                    skip_this_link = True
                    break
                    
            if skip_this_link:
                continue
                
            if job_url.startswith('/'): job_url = "https://sarkariresult.com.cm" + job_url
                
            slug = create_slug(title)
            
            print(f"\n📌 [{cat['label']}] [{valid_links_processed + 1}/10] Checking: {title}")
            
            existing_docs = db.collection(cat["collection"]).where(filter=FieldFilter('slug', '==', slug)).get()
            if len(existing_docs) > 0:
                print("⚠️ Database mein pehle se hai. Skipping...")
                valid_links_processed += 1
                continue 
                
            print("⏳ Data nikal rahe hain...")
            inner_data = scrape_inner_details(job_url)
            
            if not inner_data:
                print("❌ Data nikalne mein error aayi.")
                continue
                
            print("✅ HTML ban raha hai (Premium SEO Blocks ke sath)...")
            final_html = generate_seo_html(title, inner_data, cat["label"])

            # 👇 YEH NAYI LINE YAHAN ADD KARNI HAI 👇
            final_html = final_html.replace('sarkariresult.com.cm', 'studenthelpclub.in').replace('Sarkari Result', 'Student Help Club')

            print(f"☁️ Firebase ({cat['collection']}) mein upload ho raha hai...")
            db.collection(cat["collection"]).add({
                'title': title,
                'slug': slug,
                'details': final_html,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            print("✅ Firebase Upload Successful!")
            
            post_url = f"https://jobs.studenthelpclub.in/post.html?col={cat['collection']}&slug={slug}"
            safe_title = urllib.parse.quote(title)
            safe_url = urllib.parse.quote(post_url)
            final_trigger_url = f"{GOOGLE_SERVER_URL}?title={safe_title}&url={safe_url}"
            
            try:
                trig_resp = requests.get(final_trigger_url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True, timeout=15)
                print(f"📢 Telegram / WhatsApp Message Bhej diya gaya! (Status: {trig_resp.status_code})")
            except Exception as e:
                print("⚠️ Telegram trigger fail hua:", e)
            # Firebase upload aur Telegram ke turant baad yahan call karein 👇
            notify_google_indexing(post_url)
            
            valid_links_processed += 1
            time.sleep(3) 
            
        if valid_links_processed == 0:
            print(f"⚠️ {cat['label']} mein ek bhi valid link nahi mili. Shayad saare links kachra the (Filter ho gaye) ya dabba khali tha.")

    print("\n🎉 MASTER AUTOMATION COMPLETELY FINISHED! Aapka portal ab puri tarah auto-update ho gaya hai.")
    
    # SITEMAP FUNCTION KO YAHAN CALL KARNA HAI 👇
    generate_sitemap(db)


# --- 7. AUTOMATIC SITEMAP GENERATOR ---
def generate_sitemap(db):
    import datetime
    print("⏳ Generating Sitemap...")
    
    # Aapka original static sitemap template
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset
      xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
<!-- created with Free Online Sitemap Generator www.xml-sitemaps.com -->

<url>
  <loc>https://jobs.studenthelpclub.in/</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>1.00</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/index.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/jobs.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/admit-cards.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/results.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/yojna.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/scholarship.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/about.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/contact.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/privacy-policy.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
<url>
  <loc>https://jobs.studenthelpclub.in/disclaimer.html</loc>
  <lastmod>2026-04-24T16:18:41+00:00</lastmod>
  <priority>0.80</priority>
</url>
"""

    today_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    collections = ['jobs', 'admit', 'result']
    
    # Firebase se dynamic posts uthana
    for col in collections:
        docs = db.collection(col).stream()
        for doc in docs:
            data = doc.to_dict()
            slug = data.get('slug')
            if slug:
                post_url = f"https://jobs.studenthelpclub.in/post.html?col={col}&amp;slug={slug}"
                sitemap_content += f"""
<url>
  <loc>{post_url}</loc>
  <lastmod>{today_date}</lastmod>
  <priority>0.80</priority>
</url>"""

    sitemap_content += "\n</urlset>"

    # XML File ko save karna
    with open("sitemap.xml", "w", encoding="utf-8") as file:
        file.write(sitemap_content)
    
    print("✅ Sitemap automatically generated as sitemap.xml!")


# SCRIPT START HONE KA ASLI POINT YAHAN HAI 👇
if __name__ == "__main__":
    run_automation()
