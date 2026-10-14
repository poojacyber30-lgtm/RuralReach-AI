"""Rural Scheme AI — single-file native Python desktop app.

The Tkinter GUI, scheme lookup logic, chat history, and bundled scheme data
are all contained in this one Python file. No API keys or web frontend.
Optional voice I/O uses local faster-whisper and pyttsx3.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "Rural Scheme AI"
APP_DIR = Path.home() / ".namma_thittam_ai"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = APP_DIR / "chat_history.db"
LOG_FILE = APP_DIR / "app.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Dark, WhatsApp-inspired palette; all widgets are native Tkinter desktop widgets.
BG = "#0b141a"
SIDEBAR = "#111b21"
PANEL = "#202c33"
PANEL_2 = "#263640"
BUBBLE_BOT = "#202c33"
BUBBLE_USER = "#005c4b"
TEXT = "#e9edef"
MUTED = "#aebac1"
GREEN = "#00a884"
GREEN_HOVER = "#06cf9c"
BORDER = "#2b3b45"
WARN = "#f6c56f"

# Approximate Tamil-script-to-Latin transliteration for Tanglish responses.
_VOWELS = {"அ":"a", "ஆ":"aa", "இ":"i", "ஈ":"ee", "உ":"u", "ஊ":"oo", "எ":"e", "ஏ":"ae", "ஐ":"ai", "ஒ":"o", "ஓ":"oh", "ஔ":"au", "ஃ":"ah"}
_CONS = {"க":"k", "ங":"ng", "ச":"ch", "ஞ":"nj", "ட":"t", "ண":"n", "த":"th", "ந":"n", "ப":"p", "ம":"m", "ய":"y", "ர":"r", "ல":"l", "வ":"v", "ழ":"zh", "ள":"l", "ற":"tr", "ன":"n", "ஜ":"j", "ஷ":"sh", "ஸ":"s", "ஹ":"h", "க்ஷ":"ksh"}
_SIGNS = {"ா":"aa", "ி":"i", "ீ":"ee", "ு":"u", "ூ":"oo", "ெ":"e", "ே":"ae", "ை":"ai", "ொ":"o", "ோ":"oh", "ௌ":"au", "்":""}
_TAMIL_BLOCK = re.compile(r"[\u0B80-\u0BFF]")


# Curated Tanglish content. These are deliberately human-readable Roman-script Tamil,
# rather than character-by-character transliteration, which often sounds robotic.
TANGLISH_LABELS = [
    "Thittaththin nokkam", "Nanmaigal", "Yaarukku thagudhi irukkum?",
    "Thevaiyaana documents", "Eppadi apply pannalaam?", "Mukkiya kurippugal",
    "Documents patriya kurippu", "Official website",
]
TANGLISH_SCHEME_DETAILS = {
    "pm_kisan": {
        "name": "PM-KISAN Samman Nidhi",
        "summary": "PM-KISAN enbadhu, thagudhiyaana nilam ulla vivasaya kudumbangalukku maththiya arasu vazhangum varumaana uthavi thittam. Tharpoathaiya vidhigal matrum saripaarppukku utpattu, aandukku moththam 6,000 rupees moonru thavanaigalil kidaikkum.",
        "benefits": "Aandhukku 6,000 rupees, moonru samamaana thavanaigalil payanaalarin bank account-ku Direct Benefit Transfer (DBT) moolamaaga anuppappadum. Registered beneficiaries-ku eKYC kattayam.",
        "eligibility": "Pothuvaaga, maanila arasaal saripaarikkappadum thagudhiyaana nilam ulla vivasaya kudumbangalukku indha thittam. Sila government-service categories, income-tax payers matrum kurippitta professional categories-ku vidhivilakku irukkalaam. Nilam irukiradhu enbadharkaaga mattum thagudhi urudhiyaagathu; latest official rules-ai check pannunga.",
        "documents": "Pothuvaaga Aadhaar, active bank account details, mobile number, matrum nilam sambandhamaana patta/land records thevaippadalaam. Ungal case-ku exact list maaralaam; official portal alladhu local agriculture/revenue office-la urudhi pannunga.",
        "apply": "Official PM-KISAN website-la New Farmer Registration-ai select pannunga. Aadhaar authentication mudiththu ketkappadum details-ai submit pannunga. Application status matrum eKYC-ai adhe portal-la check pannalaam. Udhavi thevai endraal local agriculture office alladhu CSC centre-ai anugunga.",
        "notes": "Installment, verification status matrum eligibility current central government rules-ai poruththu maaralaam. Udhavi seivadhaga sollum yaaridamum Aadhaar OTP-ai share pannaadheenga.",
        "document_note": "Ungal application status matrum portal process-ai poruththu documents maaralaam.",
        "official_name": "PM-KISAN official website",
    },
    "pmfby": {
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "summary": "PMFBY enbadhu payir kaappittu thittam. Arivikkappatta payirgalukku, arivikkappatta sila iyarkkai idarpaadugalinaal erpadum payir izhappukalukku kaappittu paadhukaappu vazhangum.",
        "benefits": "Kaappittu coverage, premium, kadaisi thethi matrum claim process aagiyavai payir, season matrum ungal pagudhiyin current notification-ai poruththu maarum.",
        "eligibility": "Arivikkappatta pagudhiyil arivikkappatta payir valarkkum vivasayigal current enrollment rules-ai meet panna vendum. Ungal oorukkum payirukkum indha season-la scheme open-a irukkiradha check pannunga.",
        "documents": "Aadhaar/identity details, bank account matrum IFSC, nilap pathivu alladhu porundhum idathil tenancy proof, payir matrum vidhai-tha thethi details thevaippadalaam. Official application process additional documents ketkalaam.",
        "apply": "Official PMFBY website-la current season matrum eligible crops-ai check pannunga. Anumadhikkappatta bank, CSC alladhu Farmer Corner vazhiyaaga apply pannunga. Receipt-ai paththiramaaga vaiththu, payir izhappu erpattaal arivikkappatta time limit-kul report pannunga.",
        "notes": "Payir kaappittu dates matrum coverage ovvoru season-ilum maaralaam. Pazhaiya deadline-ai nambaamal latest official notification-ai paarunga.",
        "document_note": "Payir, season, nilaththin nilai matrum application channel-ai poruththu documents maarum.",
        "official_name": "PMFBY official website",
    },
    "uzhavar_pathukappu": {
        "name": "Chief Minister's Uzhavar Pathukappu Thittam",
        "summary": "Idhu Tamil Nadu arasin welfare thittam. Padhivu seydha thagudhiyaana vivasaya kudumbangal matrum vivasaya thozhilaalargalukku kurippitta vagaiyana uthavigalai vazhangugiradhu. Ellorukkum ore maadhiri cash benefit kidaikkum endru artham illai.",
        "benefits": "Uthavi category-ai poruththu social-security support matrum arivikkappatta welfare uthavigal kidaikkalaam. Exact benefit matrum amount-ai current Revenue Department rules-la confirm pannunga.",
        "eligibility": "Eligibility, uthavi category matrum registration rules-ai poruththu maarum. Thozhil, vayadhu, family status, nilam/asset details pondravai check seyyappadalaam. VAO alladhu Revenue Department office-la current rules-ai ketkunga.",
        "documents": "Aadhaar/identity proof, residence proof alladhu ration card, age proof, vivasaya thozhilaalar registration/occupation proof, bank details, photo matrum category-specific certificates thevaippadalaam. Exact checklist-ai VAO-idam ketkunga.",
        "apply": "Mudhalil Village Administrative Officer (VAO) alladhu local Revenue Department office-ai anugunga. Ungalukku porundhum Uzhavar Pathukappu assistance category enna endru ketttu, current form matrum documents-ai submit pannunga. Acknowledgement-ai vaiththirunga.",
        "notes": "Benefits matrum conditions assistance category-ai poruththu maarum. Apply pannum mun district office-la latest procedure-ai confirm pannunga.",
        "document_note": "Thevaiyaana documents-ai VAO alladhu Revenue Department office-la urudhi pannunga.",
        "official_name": "Tamil Nadu Revenue Department information",
    },
    "pudhumai_penn": {
        "name": "Pudhumai Penn Scheme",
        "summary": "Pudhumai Penn enbadhu, thagudhiyaana government alladhu qualifying government-aided school-il padiththu, pin higher education thodarum maanavigalukkaana Tamil Nadu arasin uthavi thittam.",
        "benefits": "Published scheme details-padi, thagudhi ulla maanavigalukku eligible higher education padikkum kaalathil maadham 1,000 rupees bank account-ku direct-aaga varalaam. Current rules matrum course conditions porundhum.",
        "eligibility": "Published guidance-padi, 6 mudhal 12-vadhu vaguppu varai qualifying government school alladhu qualifying government-aided Tamil-medium school-il padiththu, pin eligible higher education course-il serndhirukka vendum. School, course matrum institution eligibility-ai confirm pannunga.",
        "documents": "School study certificate, community certificate, income certificate, bank passbook/account details, Aadhaar matrum college admission proof ketkappadalaam. College additional records ketkalaam.",
        "apply": "College scholarship alladhu student welfare office-ai anugi current UMIS application process-ai ketkunga. Ketta documents-ai submit pannitu, college application-ai verify/forward seydhadhaa confirm pannunga.",
        "notes": "Eligibility matrum application dates maaralaam. College matrum current official notice-la latest details-ai verify pannunga.",
        "document_note": "College-in current checklist-ai follow pannunga; documents maaralaam.",
        "official_name": "Pudhumai Penn scheme information",
    },
    "tamil_pudhalvan": {
        "name": "Tamil Pudhalvan Scheme",
        "summary": "Tamil Pudhalvan enbadhu, qualifying school education mudiththu higher education thodarum thagudhiyaana maanavargalukkaana Tamil Nadu arasin uthavi thittam.",
        "benefits": "Published scheme details-padi, thagudhi ulla maanavargalukku eligible higher education padikkum kaalathil maadham 1,000 rupees direct bank transfer moolamaaga kidaikkalaam. Current rules matrum course conditions porundhum.",
        "eligibility": "Published guidance-padi, 6 mudhal 12-vadhu vaguppu varai qualifying government school alladhu qualifying government-aided Tamil-medium school-il padiththu, pin eligible higher education course-il serndhirukka vendum. Ungal school matrum course eligibility-ai institution-idam confirm pannunga.",
        "documents": "School study certificate, community certificate, income certificate, bank passbook/account details, Aadhaar matrum college admission proof ketkappadalaam. Exact requirements-ai college-idam confirm pannunga.",
        "apply": "College student welfare alladhu scholarship office-ai contact panni current UMIS process-ai kelunga. Requested records submit pannitu, application verify seydhu forward pannappattadhaa check pannunga.",
        "notes": "Eligibility matrum application window maaralaam. College matrum latest government notification-la confirm pannunga.",
        "document_note": "College-in current checklist-ai confirm pannunga.",
        "official_name": "Tamil Pudhalvan scheme information",
    },
    "kmut": {
        "name": "Kalaignar Magalir Urimai Thittam",
        "summary": "Indha Tamil Nadu thittam, thagudhiyaana kudumba thalaivigalukku maadha financial assistance vazhangugiradhu. Government eligibility rules matrum verification porundhum.",
        "benefits": "Official state materials-padi, thagudhi ulla payanaaligalukku maadham 1,000 rupees direct transfer moolamaaga vazhangappadum endru vivarikkappattulladhu. Current notification matrum beneficiary status-ai confirm pannunga.",
        "eligibility": "Kudumba thalaivi ennum definition, income, assets, household details matrum exclusion rules-ai meet seyyum applicants mattume thagudhi peralaam. App ungal eligibility-ai urudhi seiyaadhu; official portal alladhu local e-Sevai centre-la check pannunga.",
        "documents": "Family/ration card, Aadhaar, bank account details, mobile number matrum current notification ketkum records-ai thayaaraga vaiththirunga. Exact list application status/workflow-ai poruththu maaralaam.",
        "apply": "Official Tamil Nadu e-Sevai service, local e-Sevai centre alladhu designated government camp moolamaaga current process-ai ketkunga. Pudhiya application, appeal matrum required documents patri latest announcement-ai paarunga.",
        "notes": "Approval guarantee seivom endru sollum unofficial agents-ai nambaadheenga; guarantee-kkaaga panam kodukkaadheenga. Amount, eligibility matrum application period maaralaam.",
        "document_note": "Personal documents submit pannum mun current official document list-ai confirm pannunga.",
        "official_name": "Kalaignar Magalir Urimai Thittam information",
    },
    "vb_gramg": {
        "name": "VB-G RAM-G Rural Employment Framework",
        "summary": "1 July 2026 mudhal, VB-G RAM-G framework MGNREGA framework-ai maatrriyulladhu endru maththiya arasu theriviththulladhu. Graamappura kudumbathil 18 vayadhukku melaana uruppinargal unskilled manual work seiya virumbinaal, wage-employment guarantee vazhangum framework idhu.",
        "benefits": "Current framework-padi, thagudhiyaana graamappura kudumbathukku oru financial year-il 125 naatkal varai wage employment guarantee vivarikkappattulladhu. Wage rate matrum operation rules current central/Tamil Nadu notification-ai poruththu maarum. Transition kaalathil existing MGNREGA job cards valid endru central FAQ koorugiradhu; local update-ai confirm pannunga.",
        "eligibility": "Graamappura kudumbathil 18+ vayadhu adult members unskilled manual work seiya thayaaraga irukkanum. Registration, job-card matrum state rules porundhum. Work alladhu payment-ai app guarantee seiyaadhu.",
        "documents": "Pudhiya registration alladhu record update-ku household member names/ages, residence details, identity/address records, photo ketkappattaal adhu, existing job-card details thevaippadalaam. Gram Panchayat-la exact current checklist-ai ketkunga.",
        "apply": "Gram Panchayat alladhu local rural development office-ai anugi current Tamil Nadu State Scheme procedure-ai kelunga. Registration/job-card update thevai endraal apply pannunga; velai demand-ai official process moolamaaga submit seydhu dated acknowledgement-ai vaiththirunga.",
        "notes": "Mukkiya current update: central government-padi VB-G RAM-G 1 July 2026-il nadaimuraikku vandhu MGNREGA-ai maatrriyulladhu. Pazhaiya 100-day details alladhu old wage rates-ai nambaamal latest Tamil Nadu notice-ai check pannunga.",
        "document_note": "State implementation-kkaana latest checklist-ai Gram Panchayat-la ketkunga.",
        "official_name": "Rural employment scheme official information",
    },
    "pmayg": {
        "name": "Pradhan Mantri Awaas Yojana – Gramin (PMAY-G)",
        "summary": "PMAY-G enbadhu graamappura pagudhigalil thagudhiyaana veedu illaadha alladhu scheme criteria-padi eligible households-kku veettu uthavi vazhangum housing programme.",
        "benefits": "Thagudhiyaana beneficiaries-kku government guidelines-padi veedu kattum financial assistance kidaikkalaam. Amount matrum installment rules current state guidelines-ai poruththu confirm seyyanum.",
        "eligibility": "Household housing condition, official survey/beneficiary list matrum exclusion criteria-ai poruththu selection nadakkum. Graamathil vasikkiradhu mattum thagudhi urudhi seiyaadhu; official verification process-ai follow pannunga.",
        "documents": "Identity, residence, household details, bank account information matrum official survey/verification-il ketkum records thevaippadalaam. Documents-ai unofficial agents-idam kodukkaadheenga.",
        "apply": "Gram Panchayat alladhu rural development office-la current survey matrum beneficiary list patri kelunga. Official PMAY-G portal-la available eligibility/status details-ai check pannunga. Final selection government verification-ai poruththadhu.",
        "notes": "Survey/selection rules matrum assistance amount maaralaam. Local authority-idam current process-ai confirm pannunga.",
        "document_note": "Survey matrum beneficiary verification-ai poruththu documents maaralaam.",
        "official_name": "PMAY-G official website",
    },
    "pmjdy": {
        "name": "Pradhan Mantri Jan-Dhan Yojana (PMJDY)",
        "summary": "PMJDY enbadhu bank account illaadha makkalukku basic savings bank account matrum financial services access kidaikka udhavum thittam.",
        "benefits": "PMJDY rules-padi minimum balance thevai illaadha basic savings account kidaikkum. Debit card insurance alladhu overdraft pondra extra benefits eligibility matrum usage conditions-ai poruththadhu; ellorukkum automatic-aaga kidaikkaadhu.",
        "eligibility": "Pothuvaaga bank account illaadhavargal bank branch alladhu authorized Bank Mitra-ai anugalaam. Current KYC rules-padi bank identity matrum account-opening eligibility-ai check seyyum.",
        "documents": "Aadhaar pothuvaaga accept seyyappadum. Aadhaar illaavittaal officially accepted alternative KYC documents enna endru bank-idam kelunga. Mobile number irundhaal eduththuch sellunga.",
        "apply": "Bank branch alladhu authorized Bank Mitra-ai anugi PMJDY/basic savings account open seiya sollunga. KYC mudiththu receipt-ai vaiththirunga. Card alladhu insurance benefits-kkaana conditions-ai padiththu paarunga.",
        "notes": "Basic account benefits-um conditional debit-card, insurance, overdraft benefits-um vera vera. Current official terms-ai check pannunga.",
        "document_note": "Accept seyyappadum KYC documents-ai bank-la confirm pannunga.",
        "official_name": "PMJDY official website",
    },
    "breakfast": {
        "name": "Tamil Nadu Chief Minister's Breakfast Scheme",
        "summary": "Indha school meal programme, pangeyrkum government primary schools-il seyalaakkappadugiradhu. Idhu family-kku cash benefit-aaga apply seyyum scheme alla; school moolamaaga breakfast vazhangappadum.",
        "benefits": "Programme coverage ulla schools-il, current government guidelines matrum local timetable-padi thagudhiyaana maanavargalukku breakfast vazhangappadum.",
        "eligibility": "Ungal school programme-il pangeyrkiradhaa, endha classes cover aagindrana enbadhai school head teacher-idam kelunga. Coverage matrum timings local arrangement-ai poruththu maaralaam.",
        "documents": "Breakfast meal-kkaaga thaniyaaga cash-benefit application document pack pothuvaaga thevai illai. School-in regular enrolment/attendance details thevaippadalaam.",
        "apply": "Ungal government primary school-ai neradiyaaga contact panni scheme nadakkiradhaa, yaarukku porundhum, timetable enna endru confirm pannunga. Regular school enrolment process-ai follow pannunga.",
        "notes": "School coverage matrum programme guidelines government update-ai poruththu maaralaam.",
        "document_note": "Additional student records thevaiyaa endru school-idam kelunga.",
        "official_name": "Tamil Nadu government scheme information",
    },
    "old_age_pension": {
        "name": "Tamil Nadu Social Security Pension Schemes",
        "summary": "Tamil Nadu-il old-age, widow matrum disability-related assistance ulla pala social-security pension categories irukkindrana. Ovvoru category-kum thani rules irukkum.",
        "benefits": "Monthly assistance amount, pension category matrum current government order-ai poruththu maarum. Latest amount-ai Revenue Department office-la confirm pannunga.",
        "eligibility": "Age, widow/disability status, income/assets, family situation matrum category-specific conditions check seyyappadalaam. Oru pension category-in age rule-ai ella category-kum apply pannaadheenga.",
        "documents": "Age proof, Aadhaar/identity, residence/ration card, bank details, photo matrum porundhum idathil disability, widowhood alladhu destitution certificates ketkappadalaam. Exact list-ai VAO/Revenue office-la perunga.",
        "apply": "Village Administrative Officer (VAO) alladhu local Revenue Department office-ai anugunga. Endha pension category-ku apply seigirirgal endru solli current form matrum document checklist-ai kelunga. Acknowledgement-ai vaiththu status eppadi check pannuvadhu endrum kelunga.",
        "notes": "Category-wise eligibility matrum amount maaralaam. Apply pannum mun local office-la current details-ai confirm pannunga.",
        "document_note": "Pension category-ai poruththu exact document list maarum.",
        "official_name": "Tamil Nadu Revenue Department information",
    },
    "tamil_nadu_sevai": {
        "name": "Tamil Nadu e-Sevai Services",
        "summary": "Tamil Nadu e-Sevai enbadhu pala government services-ai pattiyalidum official service channel. Certificate applications matrum sila scheme-related services idhil irukkalaam; service availability idaththaiyum service-aiyum poruththu maarum.",
        "benefits": "Service details, application/status options matrum government service centre vazhigalai kandupidikka udhavum. Ella schemes-um e-Sevai moolamaaga apply seyyalaam endru artham illai.",
        "eligibility": "Eligibility neenga therndhedukkum exact service-ai poruththadhu. Ovvoru certificate alladhu scheme-kum thani eligibility matrum proof thevaigal irukkum.",
        "documents": "Documents service-specific. Edhaiyum prepare/upload seivadharku mun official service-list entry-la current list-ai check pannunga.",
        "apply": "Official e-Sevai service list-ai open pannunga alladhu government e-Sevai centre-ai visit pannunga. Exact service-ai select panni documents matrum fees-ai check seydhu official process moolamaaga submit pannunga. Receipt-ai vaiththirunga.",
        "notes": "Theriyaadha website alladhu unofficial agent-idam identity documents-ai upload pannaadheenga.",
        "document_note": "Ovvoru e-Sevai service-kum documents verupadum.",
        "official_name": "Tamil Nadu e-Sevai official service list",
    },
}
TANGLISH_SCHEME_NAMES = {key: value["name"] for key, value in TANGLISH_SCHEME_DETAILS.items()}


def tanglish_for_scheme(scheme: dict, field: str, fallback: str = "") -> str:
    """Return curated Tanglish for a scheme field; transliterate only as last resort."""
    entry = TANGLISH_SCHEME_DETAILS.get(scheme.get("id", ""), {})
    value = entry.get(field)
    if value:
        return value
    return fallback


def speech_safe_text(text: str, language: str) -> str:
    """Remove URLs and visual formatting that speech engines pronounce as gibberish."""
    spoken_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Don't make the engine read a URL character by character.
        if re.search(r"https?://\S+", line):
            continue
        if re.fullmatch(r"[─━│\s]{8,}", line):
            continue
        if line.casefold() in {"official website", "அதிகாரப்பூர்வ இணையதளம்"}:
            continue
        line = line.replace("↗", "").replace("•", "")
        line = line.replace("₹", " rupees ")
        line = re.sub(r"\beKYC\b", "e K Y C", line, flags=re.IGNORECASE)
        line = re.sub(r"\bDBT\b", "D B T", line)
        line = re.sub(r"[─━│]+", " ", line)
        line = re.sub(r"\s+([,.!?])", r"\1", line)
        line = re.sub(r"\s{2,}", " ", line).strip(" .:|\t")
        if line:
            spoken_lines.append(line)
    # Sentence-length pauses sound much more natural than reading URLs and layout marks.
    return ". ".join(spoken_lines)[:12000]


def normalise(text: str) -> str:
    text = text.casefold().replace("’", "'")
    text = re.sub(r"[^\w\u0B80-\u0BFF]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


_SCHEMES_JSON = '[{"id":"pm_kisan","name_en":"PM-KISAN Samman Nidhi","name_ta":"பிரதம மந்திரி கிசான் சம்மான் நிதி","category":"Farmers","aliases":["pm kisan","pm-kisan","pmkisan","kisan samman nidhi","farmer 6000","vivasayi 6000","vivasayigal thittam","கிசான்","பிஎம் கிசான்"],"summary_en":"A Central Sector income-support scheme for eligible landholding farmer families. The scheme provides ₹6,000 per year in three instalments, subject to current eligibility rules and verification.","summary_ta":"தகுதியுடைய நிலம் வைத்துள்ள விவசாயக் குடும்பங்களுக்கு மத்திய அரசு வழங்கும் வருமான ஆதரவுத் திட்டம். தற்போதைய தகுதி விதிகள் மற்றும் சரிபார்ப்புக்கு உட்பட்டு ஆண்டுக்கு ₹6,000 மூன்று தவணைகளாக வழங்கப்படுகிறது.","benefits_en":"₹6,000 per year in three equal instalments, transferred to the beneficiary bank account by Direct Benefit Transfer (DBT). eKYC is mandatory for registered beneficiaries.","benefits_ta":"ஆண்டுக்கு ₹6,000 மூன்று சம தவணைகளாக நேரடியாக வங்கிக் கணக்கில் (DBT) செலுத்தப்படும். பதிவு செய்த பயனாளிகளுக்கு eKYC கட்டாயம்.","eligibility_en":"Generally for eligible landholding farmer families, as identified and verified by the State. Exclusion rules apply, including certain institutional landholders, income-tax payers and specified government-service or professional categories. Do not assume every landowner qualifies; check the current official criteria.","eligibility_ta":"பொதுவாக மாநில அரசால் அடையாளம் கண்டு சரிபார்க்கப்படும் தகுதியான நிலம் வைத்துள்ள விவசாயக் குடும்பங்களுக்கு. நிறுவன நில உரிமையாளர்கள், வருமானவரி செலுத்துவோர் மற்றும் குறிப்பிட்ட அரசு ஊழியர் அல்லது தொழில்முறை பிரிவுகள் உள்ளிட்ட விலக்கு விதிகள் உள்ளன. நிலம் இருப்பதாலேயே அனைவரும் தகுதி பெறுவார்கள் என கருத வேண்டாம்; தற்போதைய அதிகாரப்பூர்வ விதிகளைச் சரிபார்க்கவும்.","documents_en":"Usually needed: Aadhaar, active bank account details, mobile number, and land-ownership/land-record details. The portal may request authentication or additional records; confirm the exact checklist with the official portal or local agriculture/revenue office.","documents_ta":"பொதுவாக ஆதார், செயல்பாட்டிலுள்ள வங்கிக் கணக்கு விவரங்கள், கைப்பேசி எண் மற்றும் நில உரிமை/நிலப் பதிவுகள் தேவைப்படும். இணையதளம் கூடுதல் சரிபார்ப்பு அல்லது ஆவணங்களை கேட்கலாம்; சரியான பட்டியலை அதிகாரப்பூர்வ தளம் அல்லது உள்ளூர் வேளாண்மை/வருவாய் அலுவலகத்தில் உறுதி செய்யவும்.","apply_en":"Open the official PM-KISAN portal and use New Farmer Registration. Complete Aadhaar authentication and submit the requested details. Track status and eKYC on the same portal, or ask the local agriculture office/CSC for assistance.","apply_ta":"அதிகாரப்பூர்வ PM-KISAN இணையதளத்தில் New Farmer Registration என்பதைத் தேர்ந்தெடுக்கவும். ஆதார் சரிபார்ப்பை முடித்து கேட்ட விவரங்களைச் சமர்ப்பிக்கவும். அதே தளத்தில் விண்ணப்ப நிலை மற்றும் eKYC-ஐப் பார்க்கலாம்; உதவிக்கு உள்ளூர் வேளாண்மை அலுவலகம் அல்லது CSC மையத்தை அணுகவும்.","notes_en":"Installments, verification status and eligibility are governed by current central guidelines and may change. Never share an Aadhaar OTP with anyone claiming to help.","notes_ta":"தவணை, சரிபார்ப்பு நிலை மற்றும் தகுதி தற்போதைய மத்திய அரசு வழிகாட்டுதலின் அடிப்படையில் மாறலாம். உதவி செய்வதாகக் கூறுபவர்களிடம் ஆதார் OTP-ஐ பகிர வேண்டாம்.","documents_note":"Exact document requirements can vary by case and portal workflow.","official_url":"https://pmkisan.gov.in/","official_name":"PM-KISAN official portal"},{"id":"pmfby","name_en":"Pradhan Mantri Fasal Bima Yojana (PMFBY)","name_ta":"பிரதம மந்திரி பசல் பீமா யோஜனா (பயிர் காப்பீடு)","category":"Farmers","aliases":["pmfby","fasal bima","crop insurance","payir kaapidu","payir kappidu","பயிர் காப்பீடு","பயிர் காப்பீட்டுத் திட்டம்"],"summary_en":"A crop-insurance scheme intended to protect eligible farmers against specified crop losses from notified natural risks, subject to scheme terms and notified crops/seasons.","summary_ta":"அறிவிக்கப்பட்ட பயிர்கள் மற்றும் பருவங்களுக்கு பொருந்தும் விதிகளின் கீழ், குறிப்பிட்ட இயற்கை காரணங்களால் ஏற்படும் பயிர் இழப்புகளுக்கு தகுதியான விவசாயிகளுக்கு காப்பீட்டு பாதுகாப்பு வழங்கும் திட்டம்.","benefits_en":"Insurance protection for notified crops and risks. Premium rates, cut-off dates, eligible risks and claim assessment depend on the crop, season and current notification for the area.","benefits_ta":"அறிவிக்கப்பட்ட பயிர்கள் மற்றும் அபாயங்களுக்கு காப்பீட்டு பாதுகாப்பு. பிரீமியம், கடைசி தேதி, காப்பீடு செய்யப்படும் அபாயங்கள் மற்றும் இழப்பீட்டு மதிப்பீடு பயிர், பருவம், பகுதி அறிவிப்பைப் பொறுத்தது.","eligibility_en":"Farmers growing notified crops in notified areas who meet the current enrollment conditions. Coverage and enrollment deadlines vary by season and crop; check that the scheme is open for your village and crop.","eligibility_ta":"அறிவிக்கப்பட்ட பகுதியில் அறிவிக்கப்பட்ட பயிர்களைப் பயிரிடும், தற்போதைய பதிவு நிபந்தனைகளை பூர்த்தி செய்யும் விவசாயிகள். பயிர் மற்றும் பருவத்தைப் பொறுத்து காப்பீட்டு காலமும் கடைசி தேதியும் மாறும்; உங்கள் கிராமம் மற்றும் பயிருக்கு திட்டம் திறந்திருப்பதைச் சரிபார்க்கவும்.","documents_en":"Commonly requested: identity/Aadhaar details, bank account and IFSC, land record or tenancy/contract-farming proof as applicable, crop and sowing details, and farmer/contact details. The official process may ask for additional documents.","documents_ta":"பொதுவாக அடையாளம்/ஆதார் விவரங்கள், வங்கிக் கணக்கு மற்றும் IFSC, பொருந்துமிடத்தில் நிலப் பதிவு அல்லது குத்தகை/ஒப்பந்த விவசாயச் சான்று, பயிர் மற்றும் விதைப்பு விவரங்கள், விவசாயி/தொடர்பு விவரங்கள் கேட்கப்படலாம். கூடுதல் ஆவணங்கள் கேட்கப்படலாம்.","apply_en":"Check the official PMFBY portal for the current season and notified crops. Apply through the Farmer Corner or an authorized bank/CSC/approved channel listed for that season. Keep the application receipt and report crop loss within the notified time window.","apply_ta":"தற்போதைய பருவம் மற்றும் அறிவிக்கப்பட்ட பயிர்களுக்கு அதிகாரப்பூர்வ PMFBY தளத்தைச் சரிபார்க்கவும். Farmer Corner அல்லது அந்த பருவத்தில் அங்கீகரிக்கப்பட்ட வங்கி/CSC வழியாக விண்ணப்பிக்கவும். ரசீதைப் பாதுகாத்து, அறிவிக்கப்பட்ட காலத்திற்குள் பயிர் இழப்பைத் தெரிவிக்கவும்.","notes_en":"Crop insurance dates and coverage change by season. Do not rely on an old deadline; confirm current notifications before applying.","notes_ta":"பயிர் காப்பீட்டு தேதிகளும் பாதுகாப்பும் ஒவ்வொரு பருவத்திலும் மாறலாம். பழைய கடைசி தேதியை நம்பாமல் தற்போதைய அறிவிப்பை உறுதி செய்யவும்.","documents_note":"Checklist changes by crop, season, land status and application channel.","official_url":"https://pmfby.gov.in/","official_name":"PMFBY official portal"},{"id":"uzhavar_pathukappu","name_en":"Chief Minister\'s Uzhavar Pathukappu Thittam","name_ta":"முதலமைச்சரின் உழவர் பாதுகாப்புத் திட்டம்","category":"Farmers and agricultural workers","aliases":["uzhavar pathukappu","uzhavar padhukaapu","uzhavar paathukappu","farmer protection scheme","agricultural labour pension","உழவர் பாதுகாப்பு","உழவர் பாதுகாப்புத் திட்டம்"],"summary_en":"A Tamil Nadu welfare scheme covering specified assistance for eligible registered agricultural families and workers. Assistance types have their own conditions; this is not one universal cash benefit for everyone.","summary_ta":"தகுதியான பதிவு செய்யப்பட்ட விவசாயக் குடும்பங்கள் மற்றும் வேளாண் தொழிலாளர்களுக்கான குறிப்பிட்ட நல உதவிகளை வழங்கும் தமிழ்நாடு அரசு திட்டம். ஒவ்வொரு உதவிக்கும் தனித்தனி நிபந்தனைகள் உள்ளன; அனைவருக்கும் ஒரே மாதிரியான தொகை கிடைக்கும் திட்டம் அல்ல.","benefits_en":"Depending on the eligible assistance category, benefits may include social-security support and other notified welfare assistance. The exact benefit and amount must be confirmed with the current Revenue Department schedule.","benefits_ta":"தகுதியான உதவி வகையைப் பொறுத்து சமூகப் பாதுகாப்பு உதவி மற்றும் அறிவிக்கப்பட்ட பிற நல உதவிகள் இருக்கலாம். சரியான உதவி மற்றும் தொகையை தற்போதைய வருவாய்த் துறை அட்டவணையில் உறுதிப்படுத்த வேண்டும்.","eligibility_en":"Depends on the assistance category and registration rules. Applicant occupation, age, family status, land/assets and other conditions may be checked. Confirm the current eligibility table with the Village Administrative Officer (VAO) or Revenue Department.","eligibility_ta":"உதவி வகை மற்றும் பதிவு விதிகளைப் பொறுத்தது. தொழில், வயது, குடும்ப நிலை, நிலம்/சொத்துக்கள் உள்ளிட்ட நிபந்தனைகள் சரிபார்க்கப்படலாம். தற்போதைய தகுதிகளை கிராம நிர்வாக அலுவலர் (VAO) அல்லது வருவாய்த் துறையில் உறுதி செய்யவும்.","documents_en":"May include Aadhaar/identity proof, residence proof or ration card, age proof, agricultural worker/farmer registration or occupation proof, bank details, photograph and category-specific certificates. Ask the VAO for the exact checklist for the assistance requested.","documents_ta":"ஆதார்/அடையாளச் சான்று, இருப்பிடச் சான்று அல்லது குடும்ப அட்டை, வயது சான்று, விவசாயி/வேளாண் தொழிலாளர் பதிவு அல்லது தொழில் சான்று, வங்கிக் கணக்கு விவரங்கள், புகைப்படம் மற்றும் உதவி வகைக்குரிய சான்றுகள் தேவைப்படலாம். சரியான பட்டியலை VAO-விடம் கேட்கவும்.","apply_en":"Start at the Village Administrative Officer (VAO) or the local Revenue Department office. Ask which Uzhavar Pathukappu assistance category applies, obtain the current form, and submit the prescribed supporting documents. Retain the acknowledgement.","apply_ta":"கிராம நிர்வாக அலுவலர் (VAO) அல்லது உள்ளூர் வருவாய் அலுவலகத்தில் தொடங்கவும். எந்த உழவர் பாதுகாப்பு உதவி வகை பொருந்தும் எனக் கேட்டு, தற்போதைய விண்ணப்பப் படிவத்தைப் பெற்று தேவையான ஆவணங்களைச் சமர்ப்பிக்கவும். ஒப்புகையைப் பாதுகாக்கவும்.","notes_en":"Benefits and conditions can change by assistance category. Confirm the latest district procedure before applying.","notes_ta":"உதவி வகையைப் பொறுத்து நிபந்தனைகள் மாறலாம். விண்ணப்பிக்கும் முன் மாவட்டத்தின் தற்போதைய நடைமுறையை உறுதி செய்யவும்.","documents_note":"Category-specific; confirm with the VAO/Revenue Department.","official_url":"https://www.cra.tn.gov.in/eleg_schemes.php","official_name":"Tamil Nadu Revenue Department scheme eligibility"},{"id":"pudhumai_penn","name_en":"Pudhumai Penn Scheme","name_ta":"புதுமைப் பெண் திட்டம்","category":"Students","aliases":["pudhumai penn","puthumai penn","pudhumai pen","girl student 1000","college scheme for girls","புதுமைப் பெண்","மூவலூர் ராமாமிர்தம்"],"summary_en":"Tamil Nadu higher-education assistance for eligible girl students who continue higher education after studying in qualifying government or government-aided schools.","summary_ta":"தகுதி பெற்ற அரசு அல்லது அரசு உதவிபெறும் பள்ளிகளில் படித்து உயர்கல்வியைத் தொடரும் மாணவிகளுக்கான தமிழ்நாடு உயர்கல்வி உதவித் திட்டம்.","benefits_en":"The published scheme information describes ₹1,000 per month paid directly to eligible students during eligible higher education, subject to the current rules and uninterrupted course conditions.","benefits_ta":"வெளியிடப்பட்ட திட்டத் தகவலின்படி, தற்போதைய விதிகள் மற்றும் படிப்பைத் தொடரும் நிபந்தனைகளுக்கு உட்பட்டு தகுதியான மாணவிகளுக்கு மாதம் ₹1,000 நேரடியாக வழங்கப்படுகிறது.","eligibility_en":"Published Tamil Nadu institute guidance describes girls who studied Classes 6–12 in government schools or qualifying government-aided Tamil-medium schools and then pursue eligible higher education. Institution/course and current government rules must be checked.","eligibility_ta":"தமிழ்நாடு அரசு நிறுவன வழிகாட்டுதலின்படி, 6–12 வகுப்புகளை அரசு பள்ளி அல்லது தகுதியான அரசு உதவிபெறும் தமிழ் வழிப் பள்ளியில் படித்து, தகுதியான உயர்கல்வியைத் தொடரும் மாணவிகள் இதில் அடங்குவர். கல்லூரி/படிப்பு மற்றும் தற்போதைய விதிகளை உறுதி செய்யவும்.","documents_en":"Published institute checklist may include school study certificate, community certificate, income certificate, bank passbook/account details, Aadhaar and college admission proof. The institution may request other records.","documents_ta":"நிறுவன வழிகாட்டுதலின் படி பள்ளிப் படிப்பு சான்று, சமூகச் சான்று, வருமானச் சான்று, வங்கிப் புத்தகம்/கணக்கு விவரம், ஆதார் மற்றும் கல்லூரி சேர்க்கைச் சான்று தேவைப்படலாம். நிறுவனம் கூடுதல் ஆவணங்கள் கேட்கலாம்.","apply_en":"Ask the college scholarship/student welfare office about the current UMIS application process. Submit the requested records and confirm that the institution has verified/forwarded the application. Use only official portals and current notices.","apply_ta":"தற்போதைய UMIS விண்ணப்ப நடைமுறையை கல்லூரி உதவித்தொகை/மாணவர் நல அலுவலகத்தில் கேட்கவும். கேட்ட ஆவணங்களைச் சமர்ப்பித்து, நிறுவனம் விண்ணப்பத்தைச் சரிபார்த்து அனுப்பியதை உறுதி செய்யவும். அதிகாரப்பூர்வ தளங்கள் மற்றும் தற்போதைய அறிவிப்புகளை மட்டும் பயன்படுத்தவும்.","notes_en":"Eligibility and application windows may change. Verify with the college and official scheme notice.","notes_ta":"தகுதி மற்றும் விண்ணப்பக் காலம் மாறலாம். கல்லூரி மற்றும் அதிகாரப்பூர்வ அறிவிப்பில் உறுதி செய்யவும்.","documents_note":"Based on published institute guidance; confirm the current college checklist.","official_url":"https://tils.tn.gov.in/schemes","official_name":"Tamil Nadu Institute of Labour Studies scheme guidance"},{"id":"tamil_pudhalvan","name_en":"Tamil Pudhalvan Scheme","name_ta":"தமிழ் புதல்வன் திட்டம்","category":"Students","aliases":["tamil pudhalvan","tamizh pudhalvan","tamil puthalvan","boy student 1000","college scheme for boys","தமிழ் புதல்வன்"],"summary_en":"Tamil Nadu higher-education assistance for eligible male students who continue higher education after qualifying school study.","summary_ta":"தகுதியான பள்ளிக் கல்விக்குப் பிறகு உயர்கல்வியைத் தொடரும் தகுதி பெற்ற மாணவர்களுக்கான தமிழ்நாடு உதவித் திட்டம்.","benefits_en":"Published scheme information describes ₹1,000 per month paid directly to eligible students during eligible higher education, subject to current rules and course conditions.","benefits_ta":"வெளியிடப்பட்ட திட்டத் தகவலின்படி, தற்போதைய விதிகள் மற்றும் படிப்பு நிபந்தனைகளுக்கு உட்பட்டு தகுதியான மாணவர்களுக்கு மாதம் ₹1,000 நேரடியாக வழங்கப்படுகிறது.","eligibility_en":"Published guidance describes boys who studied Classes 6–12 in government schools or qualifying government-aided Tamil-medium schools and then pursue eligible higher education. Confirm current course and school eligibility with the institution.","eligibility_ta":"வெளியிடப்பட்ட வழிகாட்டுதலின்படி, 6–12 வகுப்புகளை அரசு பள்ளி அல்லது தகுதியான அரசு உதவிபெறும் தமிழ் வழிப் பள்ளியில் படித்து, தகுதியான உயர்கல்வியைத் தொடரும் மாணவர்கள் இதில் அடங்குவர். தற்போதைய படிப்பு மற்றும் பள்ளித் தகுதியை நிறுவனத்தில் உறுதி செய்யவும்.","documents_en":"Published institute checklist may include school study certificate, community certificate, income certificate, bank passbook/account details, Aadhaar and college admission proof. Confirm exact requirements with the college.","documents_ta":"நிறுவன வழிகாட்டுதலின்படி பள்ளிப் படிப்பு சான்று, சமூகச் சான்று, வருமானச் சான்று, வங்கிப் புத்தகம்/கணக்கு விவரம், ஆதார் மற்றும் கல்லூரி சேர்க்கைச் சான்று தேவைப்படலாம். சரியான தேவைகளை கல்லூரியில் உறுதி செய்யவும்.","apply_en":"Contact the college student welfare/scholarship office about the current UMIS procedure. Submit requested records and ask whether the application has been verified and forwarded.","apply_ta":"தற்போதைய UMIS நடைமுறைக்காக கல்லூரி மாணவர் நல/உதவித்தொகை அலுவலகத்தை அணுகவும். கேட்ட ஆவணங்களைச் சமர்ப்பித்து, விண்ணப்பம் சரிபார்க்கப்பட்டு அனுப்பப்பட்டதா எனக் கேட்கவும்.","notes_en":"Eligibility and application windows can change. Confirm with the college and current government notification.","notes_ta":"தகுதி மற்றும் விண்ணப்பக் காலம் மாறலாம். கல்லூரி மற்றும் தற்போதைய அரசு அறிவிப்பில் உறுதி செய்யவும்.","documents_note":"Based on published institute guidance; confirm the current college checklist.","official_url":"https://tils.tn.gov.in/schemes","official_name":"Tamil Nadu Institute of Labour Studies scheme guidance"},{"id":"kmut","name_en":"Kalaignar Magalir Urimai Thittam","name_ta":"கலைஞர் மகளிர் உரிமைத் திட்டம்","category":"Women and families","aliases":["kalaignar magalir urimai","magalir urimai thogai","magalir urimai thittam","women 1000 tamil nadu","magalir 1000","மகளிர் உரிமைத் தொகை","கலைஞர் மகளிர் உரிமை"],"summary_en":"Tamil Nadu monthly financial assistance scheme for eligible women heads of households. Eligibility is subject to government criteria and verification.","summary_ta":"தகுதி பெற்ற குடும்பத் தலைவிகளுக்கு மாதாந்திர நிதி உதவி வழங்கும் தமிழ்நாடு அரசு திட்டம். அரசு நிர்ணயிக்கும் தகுதி விதிகள் மற்றும் சரிபார்ப்புக்கு உட்பட்டது.","benefits_en":"The scheme is described in official state materials as providing ₹1,000 per month to eligible beneficiaries by direct transfer, subject to current notifications and beneficiary status.","benefits_ta":"அரசின் வெளியிடப்பட்ட தகவலின்படி தகுதியான பயனாளிகளுக்கு மாதம் ₹1,000 நேரடி பணமாற்றமாக வழங்கப்படுகிறது; தற்போதைய அறிவிப்புகள் மற்றும் பயனாளர் நிலைக்கு உட்பட்டது.","eligibility_en":"Only applicants meeting the current definition of an eligible woman head of household and the scheme\'s income, asset, household and exclusion rules may qualify. This app cannot certify eligibility; verify the current criteria on the official service portal or with the local e-Sevai centre.","eligibility_ta":"குடும்பத் தலைவி என்ற தற்போதைய வரையறை மற்றும் திட்டத்தின் வருமானம், சொத்து, குடும்பம், விலக்கு விதிகளைப் பூர்த்தி செய்பவர்களே தகுதி பெறலாம். இந்தச் செயலி தகுதியை உறுதி செய்யாது; அதிகாரப்பூர்வ சேவைத் தளம் அல்லது உள்ளூர் e-Sevai மையத்தில் தற்போதைய விதிகளைச் சரிபார்க்கவும்.","documents_en":"Keep the family/ration card, Aadhaar, bank account details, mobile number and any records explicitly requested by the current notification ready. The exact accepted list depends on the current application/status workflow.","documents_ta":"குடும்ப/ரேஷன் அட்டை, ஆதார், வங்கிக் கணக்கு விவரங்கள், கைப்பேசி எண் மற்றும் தற்போதைய அறிவிப்பில் கேட்கப்படும் ஆவணங்களைத் தயாராக வைத்திருக்கவும். சரியான பட்டியல் விண்ணப்பம்/நிலை நடைமுறையைப் பொறுத்தது.","apply_en":"Use the official Tamil Nadu e-Sevai service for status and published application processes, or contact the local e-Sevai centre / designated government camp. Check current announcements for fresh applications, appeals and required documents.","apply_ta":"நிலை மற்றும் வெளியிடப்பட்ட விண்ணப்ப நடைமுறைக்காக தமிழ்நாடு e-Sevai சேவையைப் பயன்படுத்தவும் அல்லது உள்ளூர் e-Sevai மையம்/அரசு முகாமை அணுகவும். புதிய விண்ணப்பம், மேல்முறையீடு மற்றும் ஆவணங்கள் குறித்த தற்போதைய அறிவிப்பைச் சரிபார்க்கவும்.","notes_en":"Do not rely on unofficial agents or pay anyone to guarantee approval. Amounts, eligibility and intake periods can change.","notes_ta":"ஒப்புதல் உறுதி எனக் கூறும் அங்கீகரிக்கப்படாத முகவர்களை நம்பவோ பணம் செலுத்தவோ வேண்டாம். தொகை, தகுதி மற்றும் விண்ணப்பக் காலம் மாறலாம்.","documents_note":"Confirm the current official checklist before submitting personal documents.","official_url":"https://tnesevai.tn.gov.in/Pages/ServiceList.aspx","official_name":"Tamil Nadu e-Sevai official service list"},{"id":"vb_gramg","name_en":"Viksit Bharat – Guarantee for Rozgar and Aajeevika Mission (Gramin) (VB-G RAM-G)","name_ta":"விக்சித் பாரத் – கிராமின் வேலைவாய்ப்பு மற்றும் வாழ்வாதார உத்தரவாதத் திட்டம் (VB-G RAM-G)","category":"Rural workers","aliases":["vb-g ram-g","vb gram g","viksit bharat guarantee","mgnrega","mgnregs","nrega","100 days work","125 days work","rural job card","job card","velai uruthi thittam","ஊரக வேலை உறுதி","வேலை அட்டை","மகாத்மா காந்தி தேசிய ஊரக வேலை உறுதித் திட்டம்"],"summary_en":"As of 1 July 2026, VB-G RAM-G replaced the Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA) framework. It provides a statutory wage-employment guarantee to eligible rural households whose adult members volunteer for unskilled manual work.","summary_ta":"2026 ஜூலை 1 முதல், மகாத்மா காந்தி தேசிய ஊரக வேலை உறுதி (MGNREGA) சட்ட அமைப்புக்கு பதிலாக VB-G RAM-G நடைமுறைக்கு வந்தது. திறனற்ற கைவேலை செய்ய விரும்பும் தகுதியான ஊரகக் குடும்பங்களுக்கு சட்டப்பூர்வ கூலி வேலை உத்தரவாதம் வழங்குகிறது.","benefits_en":"The new framework guarantees 125 days of wage employment per financial year to each eligible rural household whose adult members volunteer for unskilled manual work. Wage rates and operational rules follow current central and Tamil Nadu notifications. Existing MGNREGA job cards remain valid during the transition, according to the central government implementation FAQ.","benefits_ta":"புதிய அமைப்பின் கீழ், திறனற்ற கைவேலை செய்ய விரும்பும் தகுதியான ஊரகக் குடும்பத்திற்கு ஒரு நிதியாண்டில் 125 நாட்கள் கூலி வேலை உத்தரவாதம் வழங்கப்படுகிறது. கூலி விகிதம் மற்றும் நடைமுறை தற்போதைய மத்திய மற்றும் தமிழ்நாடு அறிவிப்புகளின்படி இருக்கும். மத்திய அரசு செயலாக்கக் கேள்வி-பதில் தகவலின்படி, மாற்றக் காலத்தில் ஏற்கனவே உள்ள MGNREGA வேலை அட்டைகள் செல்லுபடியாகும்.","eligibility_en":"Rural household whose adult members (18+) are willing to undertake unskilled manual work, subject to current registration, job-card and State Scheme rules. Employment must be requested through the official channel; the app cannot guarantee selection, worksite availability or payment timing.","eligibility_ta":"திறனற்ற கைவேலை செய்யத் தயாராக உள்ள 18 வயதுக்கு மேற்பட்ட உறுப்பினர்களைக் கொண்ட ஊரகக் குடும்பம்; தற்போதைய பதிவு, வேலை அட்டை மற்றும் மாநிலத் திட்ட விதிகள் பொருந்தும். அதிகாரப்பூர்வ வழியில் வேலை கோர வேண்டும்; வேலை/பணமளிப்பு நேரத்தை இந்தச் செயலி உறுதி செய்யாது.","documents_en":"For a new registration or record update, ask the Gram Panchayat about the current State Scheme checklist. Household member names and ages, residence details, photographs if requested, identity/address records and existing job-card information may be needed. Existing MGNREGA job cards were announced as remaining valid during transition; confirm local instructions.","documents_ta":"புதிய பதிவு அல்லது விவரத் திருத்தத்திற்கு தற்போதைய மாநிலத் திட்ட ஆவணப் பட்டியலை ஊராட்சியில் கேட்கவும். குடும்ப உறுப்பினர்களின் பெயர்/வயது, இருப்பிட விவரங்கள், கேட்டால் புகைப்படங்கள், அடையாள/முகவரி ஆவணங்கள் மற்றும் பழைய வேலை அட்டை விவரங்கள் தேவைப்படலாம். மாற்றக் காலத்தில் பழைய MGNREGA வேலை அட்டைகள் செல்லுபடியாகும் என அறிவிக்கப்பட்டுள்ளது; உள்ளூர் வழிகாட்டுதலை உறுதி செய்யவும்.","apply_en":"Start with the Gram Panchayat or local rural development office and ask for the current VB-G RAM-G Tamil Nadu State Scheme procedure. Apply for registration/job-card updates if required, submit a dated work demand through the official process, and retain the acknowledgement. For disputes, ask the Panchayat or programme officer about the current grievance route.","apply_ta":"ஊராட்சி அல்லது உள்ளூர் ஊரக வளர்ச்சி அலுவலகத்தில் தற்போதைய VB-G RAM-G தமிழ்நாடு மாநிலத் திட்ட நடைமுறையை கேட்கவும். தேவையானால் பதிவு/வேலை அட்டை விவரங்களைப் புதுப்பித்து, அதிகாரப்பூர்வ முறையில் தேதி உள்ள வேலைக் கோரிக்கையைச் சமர்ப்பித்து ஒப்புகையைப் பாதுகாக்கவும். புகார்களுக்கு தற்போதைய குறைதீர் முறையை ஊராட்சி/திட்ட அலுவலரிடம் கேட்கவும்.","notes_en":"Important current update: the central government states VB-G RAM-G came into effect nationwide on 1 July 2026, replacing MGNREGA. Do not rely on old MGNREGA 100-day descriptions or wage rates; check current Tamil Nadu implementation notices.","notes_ta":"முக்கிய தற்போதைய மாற்றம்: மத்திய அரசு தகவலின்படி VB-G RAM-G 2026 ஜூலை 1 முதல் நாடு முழுவதும் நடைமுறைக்கு வந்து MGNREGA-க்கு பதிலாக உள்ளது. பழைய 100 நாள் விளக்கங்கள் அல்லது கூலி விகிதங்களை நம்ப வேண்டாம்; தமிழ்நாட்டின் தற்போதைய செயலாக்க அறிவிப்புகளைச் சரிபார்க்கவும்.","documents_note":"Ask the Gram Panchayat for the current State Scheme checklist; implementation documents can change.","official_url":"https://www.pib.gov.in/FaqDetails.aspx?ModuleId=4&NoteId=158511&lang=1&reg=3","official_name":"Government of India PIB — VB-G RAM-G Act FAQ (2026)"},{"id":"pmayg","name_en":"Pradhan Mantri Awaas Yojana – Gramin (PMAY-G)","name_ta":"பிரதம மந்திரி ஆவாஸ் யோஜனா – கிராமின்","category":"Housing","aliases":["pmayg","pmay-g","rural house scheme","housing scheme","veedu thittam","house assistance","வீடு திட்டம்","கிராமப்புற வீடு"],"summary_en":"A rural housing programme supporting eligible rural households identified under scheme processes and current government criteria.","summary_ta":"திட்ட நடைமுறை மற்றும் தற்போதைய அரசு தகுதி விதிகளின்படி அடையாளம் காணப்படும் தகுதியான ஊரகக் குடும்பங்களுக்கு வீட்டு ஆதரவு வழங்கும் திட்டம்.","benefits_en":"Financial assistance for eligible rural housing beneficiaries as governed by applicable guidelines. Assistance amount and installment rules should be confirmed in the latest state-specific guidelines.","benefits_ta":"பொருந்தும் வழிகாட்டுதலின்படி தகுதியான ஊரக வீட்டு பயனாளிகளுக்கு நிதி உதவி. தொகை மற்றும் தவணை விதிகளை தற்போதைய மாநில வழிகாட்டுதலில் உறுதி செய்யவும்.","eligibility_en":"Selection depends on official rural housing eligibility and verification, including household housing conditions and exclusion criteria. A person cannot assume they qualify only because they live in a village; use the official eligibility/survey process.","eligibility_ta":"குடும்ப வீட்டு நிலை மற்றும் விலக்கு விதிகள் உட்பட அதிகாரப்பூர்வ ஊரக வீட்டு தகுதி மற்றும் சரிபார்ப்பின் அடிப்படையில் தேர்வு நடைபெறும். கிராமத்தில் வசிப்பதாலேயே தகுதி உறுதி ஆகாது; அதிகாரப்பூர்வ தகுதி/கணக்கெடுப்பு முறையைப் பின்பற்றவும்.","documents_en":"May include identity, residence, household details, bank account information and records requested during official beneficiary survey/verification. Do not submit documents to unofficial agents.","documents_ta":"அடையாளம், இருப்பிடம், குடும்ப விவரங்கள், வங்கிக் கணக்கு தகவல் மற்றும் அதிகாரப்பூர்வ பயனாளர் கணக்கெடுப்பு/சரிபார்ப்பில் கேட்கப்படும் பதிவுகள் தேவைப்படலாம். அங்கீகரிக்கப்படாத முகவர்களிடம் ஆவணங்களை அளிக்க வேண்டாம்.","apply_en":"Check with the Gram Panchayat or rural development office about the current survey and beneficiary list. Use the official PMAY-G portal for available eligibility checks and status; selection follows government verification.","apply_ta":"தற்போதைய கணக்கெடுப்பு மற்றும் பயனாளர் பட்டியலுக்காக ஊராட்சி அல்லது ஊரக வளர்ச்சி அலுவலகத்தை அணுகவும். கிடைக்கும் தகுதி சரிபார்ப்பு மற்றும் நிலைக்கு அதிகாரப்பூர்வ PMAY-G தளத்தைப் பயன்படுத்தவும்; அரசு சரிபார்ப்பின் அடிப்படையில் தேர்வு நடக்கும்.","notes_en":"Survey/selection rules and assistance amounts may change. Confirm the current process with local authorities.","notes_ta":"கணக்கெடுப்பு/தேர்வு விதிகள் மற்றும் உதவித் தொகை மாறலாம். உள்ளூர் அதிகாரிகளிடம் தற்போதைய நடைமுறையை உறுதி செய்யவும்.","documents_note":"Exact documents depend on survey and beneficiary verification.","official_url":"https://pmayg.nic.in/","official_name":"PMAY-G official portal"},{"id":"pmjdy","name_en":"Pradhan Mantri Jan-Dhan Yojana (PMJDY)","name_ta":"பிரதம மந்திரி ஜன்-தன் யோஜனா","category":"Banking and families","aliases":["pmjdy","jan dhan","jan-dhan","bank account scheme","zero balance account","bank account thittam","ஜன் தன்","வங்கிக் கணக்கு"],"summary_en":"A financial-inclusion initiative to help people who do not have a bank account access a basic savings bank deposit account and related financial services.","summary_ta":"வங்கிக் கணக்கு இல்லாதவர்கள் அடிப்படை சேமிப்பு வங்கிக் கணக்கு மற்றும் தொடர்புடைய நிதிச் சேவைகளைப் பெற உதவும் நிதி உள்ளடக்கத் திட்டம்.","benefits_en":"A basic savings bank account with no minimum-balance requirement under PMJDY terms. Other services, debit card insurance and overdraft facilities have eligibility and usage conditions; they are not automatic for everyone.","benefits_ta":"PMJDY விதிகளின்படி குறைந்தபட்ச இருப்புத் தொகை கட்டாயமில்லாத அடிப்படை சேமிப்புக் கணக்கு. டெபிட் கார்டு காப்பீடு மற்றும் ஓவர்டிராஃப்ட் போன்ற சேவைகளுக்கு தனித்த தகுதி/பயன்பாட்டு நிபந்தனைகள் உள்ளன; அனைவருக்கும் தானாக கிடைக்காது.","eligibility_en":"Primarily people who do not already have a bank account can approach a bank branch or authorized Bank Mitra. The bank checks identity and account-opening eligibility under current KYC rules.","eligibility_ta":"முன்பே வங்கிக் கணக்கு இல்லாதவர்கள் வங்கிக் கிளை அல்லது அங்கீகரிக்கப்பட்ட Bank Mitra-வை அணுகலாம். தற்போதைய KYC விதிகளின் கீழ் வங்கி அடையாளம் மற்றும் கணக்கு திறக்கும் தகுதியைச் சரிபார்க்கும்.","documents_en":"Aadhaar is commonly accepted; if unavailable, the bank can advise on officially accepted alternative KYC documents. Bring a mobile number if available and confirm the bank\'s current document checklist.","documents_ta":"ஆதார் பொதுவாக ஏற்றுக்கொள்ளப்படுகிறது; இல்லாவிட்டால் அதிகாரப்பூர்வமாக ஏற்கப்படும் மாற்று KYC ஆவணங்களை வங்கியில் கேட்கவும். கைப்பேசி எண் இருந்தால் எடுத்துச் செல்லவும்; தற்போதைய ஆவணப் பட்டியலை உறுதி செய்யவும்.","apply_en":"Visit a bank branch or authorized Bank Mitra and request a PMJDY/basic savings account. Complete KYC and keep the account-opening receipt. Read the terms for any associated card or insurance benefit.","apply_ta":"வங்கிக் கிளை அல்லது அங்கீகரிக்கப்பட்ட Bank Mitra-வை அணுகி PMJDY/அடிப்படை சேமிப்புக் கணக்கு கேட்கவும். KYC-ஐ முடித்து கணக்கு திறப்பு ஒப்புகையைப் பாதுகாக்கவும். இணைக்கப்பட்ட அட்டை அல்லது காப்பீட்டு நன்மைகளின் நிபந்தனைகளைப் படிக்கவும்.","notes_en":"Official PMJDY information distinguishes basic account benefits from conditional debit-card, insurance and overdraft benefits.","notes_ta":"அடிப்படை கணக்கு நன்மைகள் மற்றும் நிபந்தனைக்குட்பட்ட அட்டை, காப்பீடு, ஓவர்டிராஃப்ட் நன்மைகள் வேறுபட்டவை என்பதை அதிகாரப்பூர்வ தகவலில் உறுதி செய்யவும்.","documents_note":"The bank confirms accepted KYC documents under current RBI/bank rules.","official_url":"https://www.pmjdy.gov.in/scheme","official_name":"PMJDY official scheme page"},{"id":"breakfast","name_en":"Tamil Nadu Chief Minister\'s Breakfast Scheme","name_ta":"தமிழ்நாடு முதலமைச்சரின் காலை உணவுத் திட்டம்","category":"Children and students","aliases":["breakfast scheme","school breakfast","cm breakfast","morning meal school","kalai unavu thittam","காலை உணவுத் திட்டம்","முதலமைச்சர் காலை உணவு"],"summary_en":"A school-meal programme implemented through participating government primary schools. It is delivered at school level rather than being a household cash-benefit application.","summary_ta":"பங்கேற்கும் அரசு தொடக்கப் பள்ளிகள் மூலம் செயல்படுத்தப்படும் பள்ளி காலை உணவுத் திட்டம். இது குடும்பத்திற்கான பண உதவி விண்ணப்பம் அல்ல; பள்ளி வழியாக வழங்கப்படுகிறது.","benefits_en":"Eligible pupils receive breakfast at participating schools according to the current programme guidelines and local implementation schedule.","benefits_ta":"தற்போதைய திட்ட வழிகாட்டுதல் மற்றும் உள்ளூர் நடைமுறைக்கு ஏற்ப பங்கேற்கும் பள்ளிகளில் தகுதியான மாணவர்கள் காலை உணவு பெறுகின்றனர்.","eligibility_en":"Availability depends on the school and current government programme coverage. Ask the school head teacher about participating classes, timetable and local arrangements.","eligibility_ta":"பள்ளி மற்றும் தற்போதைய அரசு திட்ட செயல்பாட்டு வரம்பைப் பொறுத்து கிடைக்கும். பங்கேற்கும் வகுப்புகள், நேர அட்டவணை மற்றும் உள்ளூர் ஏற்பாடுகளை பள்ளித் தலைமையாசிரியரிடம் கேட்கவும்.","documents_en":"There is generally no individual cash-benefit document pack to apply for the meal itself. The school may require ordinary student enrolment/attendance details under its processes.","documents_ta":"உணவுக்காக தனிப்பட்ட பண உதவி விண்ணப்ப ஆவணத் தொகுப்பு பொதுவாக இல்லை. பள்ளியின் நடைமுறைக்கேற்ப மாணவர் சேர்க்கை/வருகை விவரங்கள் தேவைப்படலாம்.","apply_en":"Contact the government primary school directly to confirm participation and the latest local arrangements. Follow the school\'s regular enrolment process.","apply_ta":"பங்கேற்பு மற்றும் தற்போதைய உள்ளூர் ஏற்பாடுகளை உறுதிசெய்ய அரசு தொடக்கப் பள்ளியை நேரடியாக அணுகவும். பள்ளியின் வழக்கமான சேர்க்கை முறையைப் பின்பற்றவும்.","notes_en":"School coverage and programme guidelines may be revised by the government.","notes_ta":"பள்ளி வரம்பும் திட்ட வழிகாட்டுதலும் அரசால் திருத்தப்படலாம்.","documents_note":"Ask the school for any student-specific records required.","official_url":"https://www.tnbudget.tn.gov.in/","official_name":"Tamil Nadu Budget and government programme information"},{"id":"old_age_pension","name_en":"Tamil Nadu Social Security Pension Schemes (including old-age pension)","name_ta":"தமிழ்நாடு சமூகப் பாதுகாப்பு ஓய்வூதியத் திட்டங்கள் (முதியோர் ஓய்வூதியம் உட்பட)","category":"Senior citizens and vulnerable people","aliases":["old age pension","senior citizen pension","muthiyor pension","widow pension","disability pension","pension thittam","முதியோர் ஓய்வூதியம்","விதவை ஓய்வூதியம்","மாற்றுத்திறனாளி ஓய்வூதியம்"],"summary_en":"Tamil Nadu administers several social-security pension categories, including old-age, widow and disability-related assistance. Each category has its own age, status, income/assets and other conditions.","summary_ta":"முதியோர், விதவை மற்றும் மாற்றுத்திறனாளிகளுக்கான உதவிகள் உட்பட பல சமூகப் பாதுகாப்பு ஓய்வூதிய வகைகளை தமிழ்நாடு அரசு செயல்படுத்துகிறது. ஒவ்வொரு வகைக்கும் வயது, நிலை, வருமானம்/சொத்து உள்ளிட்ட தனித்த நிபந்தனைகள் உள்ளன.","benefits_en":"Monthly assistance depends on the pension category and current government order. This app does not show a guaranteed amount because rates can change; confirm the latest amount with the Revenue Department.","benefits_ta":"மாதாந்திர உதவி ஓய்வூதிய வகை மற்றும் தற்போதைய அரசு ஆணையைப் பொறுத்தது. தொகை மாறக்கூடியதால் இந்தச் செயலி உறுதியான தொகையை அறிவிக்காது; வருவாய்த் துறையில் தற்போதைய தொகையை உறுதி செய்யவும்.","eligibility_en":"Requirements vary by pension category. Authorities may check age, widow/disability status, destitution, household/property status and other conditions. Do not use one category\'s age rule for all pensions.","eligibility_ta":"ஓய்வூதிய வகையைப் பொறுத்து தகுதி மாறும். வயது, விதவை/மாற்றுத்திறன் நிலை, ஆதரவற்ற நிலை, குடும்பம்/சொத்து மற்றும் பிற நிபந்தனைகள் சரிபார்க்கப்படலாம். ஒரு வகையின் வயது விதியை எல்லா ஓய்வூதியத்திற்கும் பொருத்த வேண்டாம்.","documents_en":"May include age proof, Aadhaar/identity, residence/ration card, bank details, photograph and category-specific certificates such as disability, widowhood or destitution evidence. Obtain the exact list from the VAO/Revenue office.","documents_ta":"வயது சான்று, ஆதார்/அடையாளம், இருப்பிட/குடும்ப அட்டை, வங்கிக் கணக்கு விவரம், புகைப்படம் மற்றும் மாற்றுத்திறன்/விதவை/ஆதரவற்ற நிலை போன்ற வகைக்குரிய சான்றுகள் தேவைப்படலாம். சரியான பட்டியலை VAO/வருவாய் அலுவலகத்தில் பெறவும்.","apply_en":"Visit the Village Administrative Officer (VAO) or local Revenue Department office. Specify the pension category and request the current form and official checklist. Keep an acknowledgement and ask how to track status.","apply_ta":"கிராம நிர்வாக அலுவலர் (VAO) அல்லது உள்ளூர் வருவாய் அலுவலகத்தை அணுகவும். எந்த ஓய்வூதிய வகை எனத் தெரிவித்து தற்போதைய படிவம் மற்றும் அதிகாரப்பூர்வ பட்டியலைப் பெறவும். ஒப்புகையைப் பாதுகாத்து நிலையை எப்படிப் பார்ப்பது எனக் கேட்கவும்.","notes_en":"Official category-wise eligibility and amounts can change. Confirm locally before relying on an estimate.","notes_ta":"வகை வாரியான அதிகாரப்பூர்வ தகுதி மற்றும் தொகை மாறலாம். மதிப்பீட்டை நம்புவதற்கு முன் உள்ளூரில் உறுதி செய்யவும்.","documents_note":"Category-specific; only the local Revenue office can confirm the current required list.","official_url":"https://www.cra.tn.gov.in/eleg_schemes.php","official_name":"Tamil Nadu Revenue Department eligibility information"},{"id":"tamil_nadu_sevai","name_en":"Tamil Nadu e-Sevai services","name_ta":"தமிழ்நாடு இ-சேவை மைய சேவைகள்","category":"General public services","aliases":["esevai","e-sevai","tnesevai","certificate apply","income certificate","community certificate","residence certificate","இ-சேவை","வருமானச் சான்று","சாதிச் சான்று"],"summary_en":"An official service channel listing various government services, including selected certificate applications and scheme-related services. Availability differs by service and location.","summary_ta":"சில சான்றிதழ் விண்ணப்பங்கள் மற்றும் திட்டத் தொடர்பான சேவைகள் உட்பட பல அரசு சேவைகளைப் பட்டியலிடும் அதிகாரப்பூர்வ சேவை வழி. சேவை கிடைப்பது சேவை வகை மற்றும் இடத்தைப் பொறுத்தது.","benefits_en":"Helps residents locate service descriptions, application/status services and government service-centre options. It does not mean every scheme can be applied for through e-Sevai.","benefits_ta":"சேவை விவரங்கள், விண்ணப்பம்/நிலை சேவைகள் மற்றும் அரசு சேவை மையங்களைத் தெரிந்துகொள்ள உதவும். எல்லா திட்டங்களுக்கும் e-Sevai வழியாக விண்ணப்பிக்கலாம் என்று அர்த்தமல்ல.","eligibility_en":"Depends on the specific service requested. Each certificate or scheme has its own eligibility and evidence requirements.","eligibility_ta":"கேட்கும் சேவையைப் பொறுத்தது. ஒவ்வொரு சான்றிதழ் அல்லது திட்டத்திற்கும் தனித்த தகுதி மற்றும் ஆதார ஆவணங்கள் உள்ளன.","documents_en":"Documents are service-specific. Check the official service-list entry before preparing or uploading any document.","documents_ta":"ஆவணங்கள் சேவையைப் பொறுத்தவை. ஆவணங்களைத் தயாரிப்பதற்கு அல்லது பதிவேற்றுவதற்கு முன் அதிகாரப்பூர்வ சேவைப் பட்டியலைப் பார்க்கவும்.","apply_en":"Open the official service list or visit a government e-Sevai centre. Select the exact service, review its current document list and fees, submit only through the official process, and keep the receipt.","apply_ta":"அதிகாரப்பூர்வ சேவைப் பட்டியலைத் திறக்கவும் அல்லது அரசு e-Sevai மையத்துக்குச் செல்லவும். சரியான சேவையைத் தேர்ந்தெடுத்து தற்போதைய ஆவணப் பட்டியல் மற்றும் கட்டணத்தைப் பார்த்து அதிகாரப்பூர்வ முறையில் மட்டுமே சமர்ப்பித்து ரசீதைப் பாதுகாக்கவும்.","notes_en":"Never upload identity documents to an unknown website or unofficial agent.","notes_ta":"அறியாத இணையதளம் அல்லது அங்கீகரிக்கப்படாத முகவரிடம் அடையாள ஆவணங்களைப் பதிவேற்ற வேண்டாம்.","documents_note":"Check the exact selected service; there is no single document list for all e-Sevai services.","official_url":"https://tnesevai.tn.gov.in/Pages/ServiceList.aspx","official_name":"Tamil Nadu e-Sevai service list"}]'


def load_schemes() -> list[dict]:
    """Load and minimally validate the scheme database embedded in this file."""
    payload = json.loads(_SCHEMES_JSON)
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("The embedded scheme database is empty or invalid.")
    required = {"id", "name_en", "name_ta", "official_url"}
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or not required.issubset(item):
            raise RuntimeError(f"Invalid scheme entry at position {index + 1}.")
    return payload


class ChatHistoryStore:
    """Small SQLite repository for chat history; keeps database details out of the GUI."""

    def __init__(self, path: Path):
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, timeout=8)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=8000")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, "
            "text TEXT NOT NULL, language TEXT NOT NULL, created_at TEXT NOT NULL, scheme_id TEXT)"
        )
        self._connection.commit()

    def save(self, role: str, text: str, language: str, scheme_id: str | None = None) -> None:
        with self._lock:
            with self._connection:
                self._connection.execute(
                    "INSERT INTO messages(role,text,language,created_at,scheme_id) VALUES(?,?,?,?,?)",
                    (role, text, language, datetime.now().isoformat(timespec="seconds"), scheme_id),
                )

    def recent(self, limit: int = 16) -> list[tuple[str, str, str | None]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT role,text,scheme_id FROM messages ORDER BY id DESC LIMIT ?", (max(1, int(limit)),)
            ).fetchall()
        rows.reverse()
        return rows

    def clear(self) -> None:
        with self._lock:
            with self._connection:
                self._connection.execute("DELETE FROM messages")

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class ScrollableFrame(tk.Frame):
    """Reusable canvas-backed frame with its own vertical scrollbar."""

    def __init__(self, parent, *, background: str, canvas_background: str | None = None):
        super().__init__(parent, bg=background)
        self.canvas = tk.Canvas(
            self, bg=canvas_background or background, highlightthickness=0, borderwidth=0
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.content = tk.Frame(self.canvas, bg=background)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._update_scroll_region, add="+")
        self.canvas.bind("<Configure>", self._fit_content_width, add="+")

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event):
        self.canvas.itemconfigure(self.window_id, width=max(1, event.width))


class SchemeAssistant:
    def __init__(self, schemes: list[dict]):
        self.schemes = schemes
        self.by_id = {s["id"]: s for s in schemes}

    def find_scheme(self, query: str) -> dict | None:
        q = normalise(query)
        best, best_score = None, 0
        for scheme in self.schemes:
            candidates = [scheme.get("name_en", ""), scheme.get("name_ta", "")] + scheme.get("aliases", [])
            for cand in candidates:
                c = normalise(cand)
                if not c:
                    continue
                score = 0
                if c == q:
                    score = 120 + len(c)
                elif c in q:
                    score = 80 + len(c)
                elif len(c.split()) > 1 and all(word in q for word in c.split()):
                    score = 45 + len(c)
                elif len(c.split()) == 1 and c in q.split() and len(c) >= 4:
                    # Allow distinctive single-word aliases, but avoid matching a
                    # generic query like "farmers schemes" to one random scheme.
                    score = 30 + len(c)
                if score > best_score:
                    best, best_score = scheme, score
        # Avoid selecting a scheme because of one common word such as "scheme".
        return best if best_score >= 17 else None

    def category_results(self, query: str) -> list[dict]:
        q = normalise(query)
        mapping = {
            "farmer": ("farmer", "agriculture", "vivasayi", "vivasayigal", "farmers", "வேளாண்மை", "விவசாயி", "விவசாயிகள்", "உழவர்"),
            "student": ("student", "students", "college", "school", "pudhumai", "pudhalvan", "maanavar", "மாணவர்", "மாணவி", "கல்லூரி", "பள்ளி"),
            "women": ("woman", "women", "magalir", "pen", "family", "மகளிர்", "பெண்கள்", "குடும்பம்"),
            "housing": ("house", "housing", "veedu", "home", "வீடு", "வீட்டுமனை"),
            "pension": ("pension", "old age", "senior", "widow", "disability", "ஓய்வூதியம்", "முதியோர்", "விதவை", "மாற்றுத்திறன்"),
            "rural": ("rural", "worker", "job card", "employment", "100 days", "velai", "ஊரக", "வேலை", "தொழிலாளர்"),
            "bank": ("bank", "account", "jan dhan", "banking", "வங்கி", "கணக்கு"),
            "child": ("child", "children", "breakfast", "school meal", "குழந்தை", "காலை உணவு")
        }
        matched_categories = {k for k, words in mapping.items() if any(normalise(w) in q for w in words)}
        if not matched_categories:
            return []
        results = []
        for s in self.schemes:
            text = normalise(s.get("category", "") + " " + s.get("name_en", "") + " " + s.get("name_ta", "") + " " + " ".join(s.get("aliases", [])))
            cat = normalise(s.get("category", ""))
            if any(any(normalise(w) in text for w in mapping[k]) or k in cat for k in matched_categories):
                if s not in results:
                    results.append(s)
        # Some straightforward category fallbacks.
        if "farmer" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"pm_kisan", "pmfby", "uzhavar_pathukappu"}]
        elif "student" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"pudhumai_penn", "tamil_pudhalvan", "breakfast"}]
        elif "women" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"kmut", "old_age_pension"}]
        elif "housing" in matched_categories:
            results = [s for s in self.schemes if s["id"] == "pmayg"]
        elif "pension" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"old_age_pension", "uzhavar_pathukappu"}]
        elif "rural" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"mgnrega", "uzhavar_pathukappu", "pmayg"}]
        elif "bank" in matched_categories:
            results = [s for s in self.schemes if s["id"] == "pmjdy"]
        elif "child" in matched_categories:
            results = [s for s in self.schemes if s["id"] in {"breakfast", "pudhumai_penn", "tamil_pudhalvan"}]
        return results

    def format_scheme(self, scheme: dict, lang: str) -> str:
        is_ta = lang == "Tamil"
        is_tanglish = lang == "Tanglish"
        field_map = {
            "summary_en": ("summary", "summary_ta"),
            "benefits_en": ("benefits", "benefits_ta"),
            "eligibility_en": ("eligibility", "eligibility_ta"),
            "documents_en": ("documents", "documents_ta"),
            "apply_en": ("apply", "apply_ta"),
            "notes_en": ("notes", "notes_ta"),
        }
        def val(en_key: str, ta_key: str) -> str:
            if is_tanglish:
                tanglish_key = field_map.get(en_key, ("", ""))[0]
                return tanglish_for_scheme(scheme, tanglish_key, scheme.get(en_key, ""))
            return scheme.get(ta_key if is_ta else en_key, "")
        if is_ta:
            title = scheme["name_ta"]
            labels = ["திட்டத்தின் நோக்கம்", "நன்மைகள்", "யார் தகுதி பெறலாம்?", "தேவையான ஆவணங்கள்", "எப்படி விண்ணப்பிப்பது?", "முக்கிய குறிப்புகள்", "ஆவணக் குறிப்பு", "அதிகாரப்பூர்வ இணையதளம்"]
        elif is_tanglish:
            title = tanglish_for_scheme(scheme, "name", scheme["name_en"])
            labels = TANGLISH_LABELS
        else:
            title = scheme["name_en"]
            labels = ["Purpose", "Benefits", "Who may qualify", "Documents to prepare", "How to apply", "Important notes", "Document checklist note", "Official website"]
        # The original bundled records store this small note only in English.
        # Provide Tamil equivalents as well; Tanglish mode transliterates these.
        document_notes_ta = {
            "pm_kisan": "ஒவ்வொரு விண்ணப்பதாரரின் நிலை மற்றும் இணையதள நடைமுறையைப் பொறுத்து தேவையான ஆவணங்கள் மாறலாம்.",
            "pmfby": "பயிர், பருவம், நிலத்தின் நிலை மற்றும் விண்ணப்பிக்கும் வழியைப் பொறுத்து ஆவணப் பட்டியல் மாறும்.",
            "uzhavar_pathukappu": "உதவி வகையைப் பொறுத்த ஆவணப் பட்டியலை கிராம நிர்வாக அலுவலர் அல்லது வருவாய்த் துறையிடம் உறுதி செய்யவும்.",
            "pudhumai_penn": "நிறுவனத்தின் தற்போதைய வழிகாட்டுதலின் அடிப்படையில், கல்லூரியிடம் சரியான ஆவணப் பட்டியலை உறுதி செய்யவும்.",
            "tamil_pudhalvan": "நிறுவனத்தின் தற்போதைய வழிகாட்டுதலின் அடிப்படையில், கல்லூரியிடம் சரியான ஆவணப் பட்டியலை உறுதி செய்யவும்.",
            "kmut": "தனிப்பட்ட ஆவணங்களைச் சமர்ப்பிக்கும் முன் தற்போதைய அதிகாரப்பூர்வ ஆவணப் பட்டியலை உறுதி செய்யவும்.",
            "vb_gramg": "மாநிலத்தின் தற்போதைய நடைமுறைக்கான ஆவணப் பட்டியலை கிராம ஊராட்சியிடம் கேட்கவும்; நடைமுறைகள் மாறலாம்.",
            "pmayg": "கணக்கெடுப்பு மற்றும் பயனாளி சரிபார்ப்பைப் பொறுத்து தேவையான ஆவணங்கள் மாறும்.",
            "pmjdy": "தற்போதைய RBI மற்றும் வங்கி விதிகளின்படி ஏற்றுக்கொள்ளப்படும் KYC ஆவணங்களை வங்கியிடம் உறுதி செய்யவும்.",
            "breakfast": "மாணவருக்குத் தேவையான கூடுதல் ஆவணங்கள் உள்ளனவா என்பதைப் பள்ளியிடம் கேட்கவும்.",
            "old_age_pension": "உதவி வகையைப் பொறுத்த ஆவணப் பட்டியலை உள்ளூர் வருவாய் அலுவலகத்தில் மட்டுமே உறுதி செய்ய முடியும்.",
            "tamil_nadu_sevai": "ஒவ்வொரு e-Sevai சேவைக்கும் ஆவணங்கள் வேறுபடும்; தேர்ந்தெடுத்த சேவைக்கான பட்டியலைச் சரிபார்க்கவும்.",
        }
        document_note = scheme.get("documents_note", "")
        if is_ta or is_tanglish:
            document_note = document_notes_ta.get(scheme.get("id", ""), "தேவையான ஆவணங்கள் திட்டத்தைப் பொறுத்து மாறலாம்; அதிகாரப்பூர்வ அலுவலகத்தில் உறுதி செய்யவும்.")
            if is_tanglish:
                document_note = tanglish_for_scheme(scheme, "document_note", "Thevaiyaana documents scheme-ai poruththu maaralaam; official office-la confirm pannunga.")

        sections = [
            (labels[0], val("summary_en", "summary_ta")),
            (labels[1], val("benefits_en", "benefits_ta")),
            (labels[2], val("eligibility_en", "eligibility_ta")),
            (labels[3], val("documents_en", "documents_ta")),
            (labels[4], val("apply_en", "apply_ta")),
            (labels[5], val("notes_en", "notes_ta")),
            (labels[6], document_note),
        ]
        body = title + "\n" + ("─" * min(48, max(14, len(title)))) + "\n\n"
        for label, content in sections:
            body += f"{label}\n{content}\n\n"
        official_names_ta = {
            "pm_kisan": "PM-KISAN அதிகாரப்பூர்வ இணையதளம்",
            "pmfby": "PMFBY அதிகாரப்பூர்வ இணையதளம்",
            "uzhavar_pathukappu": "தமிழ்நாடு வருவாய்த் துறை திட்டத் தகுதி தகவல்",
            "pudhumai_penn": "புதுமைப் பெண் திட்ட அதிகாரப்பூர்வ தகவல்",
            "tamil_pudhalvan": "தமிழ் புதல்வன் திட்ட அதிகாரப்பூர்வ தகவல்",
            "kmut": "கலைஞர் மகளிர் உரிமைத் திட்ட அதிகாரப்பூர்வ தகவல்",
            "vb_gramg": "ஊரக வேலைவாய்ப்பு திட்ட அதிகாரப்பூர்வ தகவல்",
            "pmayg": "PMAY-G அதிகாரப்பூர்வ இணையதளம்",
            "pmjdy": "PMJDY அதிகாரப்பூர்வ திட்டப் பக்கம்",
            "breakfast": "தமிழ்நாடு அரசு திட்டத் தகவல்",
            "old_age_pension": "தமிழ்நாடு வருவாய்த் துறை தகுதி தகவல்",
            "tamil_nadu_sevai": "தமிழ்நாடு இ-சேவை அதிகாரப்பூர்வ சேவைப் பட்டியல்",
        }
        official_name = scheme.get("official_name", "Official source")
        if is_ta or is_tanglish:
            official_name = official_names_ta.get(scheme.get("id", ""), "அதிகாரப்பூர்வ அரசு தகவல்")
            if is_tanglish:
                official_name = tanglish_for_scheme(scheme, "official_name", official_name)
        body += f"{labels[7]}\n{official_name}: {scheme.get('official_url','')}\n\n"
        disclaimer_en = "Scheme rules, amounts and application windows can change. This offline guide is informational, not an eligibility decision. Please verify the latest official notice before applying."
        disclaimer_ta = "திட்ட விதிகள், தொகைகள் மற்றும் விண்ணப்பக் காலங்கள் மாறலாம். இந்த ஆஃப்லைன் வழிகாட்டி தகவலுக்காக மட்டுமே; இது தகுதி முடிவு அல்ல. விண்ணப்பிக்கும் முன் சமீபத்திய அதிகாரப்பூர்வ அறிவிப்பை உறுதி செய்யவும்."
        disclaimer_tanglish = "Scheme rules, amount matrum application dates maaralaam. Indha offline guide thagavalukkaaga mattume; idhu official eligibility decision alla. Apply pannum mun latest official notice-ai verify pannunga."
        disclaimer = disclaimer_ta if is_ta else disclaimer_tanglish if is_tanglish else disclaimer_en
        body += disclaimer
        return body

    def answer(self, query: str, lang: str) -> tuple[str, dict | None]:
        q = normalise(query)
        if not q:
            return self.greeting(lang), None
        words = set(q.split())
        if q in {"hello", "hi", "hey", "vanakkam", "வணக்கம்"} or ((words & {"help", "உதவி"}) and not self.find_scheme(query)):
            return self.greeting(lang), None
        # Only list every scheme when the user explicitly asks for a list.
        # Avoid treating any question that merely mentions "schemes" as a list request.
        list_phrases = (
            "list schemes", "all schemes", "show schemes", "scheme list",
            "list all schemes", "thittam list", "ella thittam list",
            "திட்டங்களின் பட்டியல்", "அனைத்து திட்டங்களின் பட்டியல்",
            "எல்லா திட்டங்களின் பட்டியல்", "திட்டங்கள் பட்டியல்",
            "அனைத்து திட்டங்கள்", "எல்லா திட்டங்கள்", "திட்டங்களை பட்டியலிடு",
        )
        if any(x in q for x in list_phrases):
            return self.list_schemes(lang), None
        found = self.find_scheme(query)
        if found:
            return self.format_scheme(found, lang), found
        categories = self.category_results(query)
        if categories:
            if lang == "Tamil":
                header = "உங்கள் கேள்விக்கு தொடர்புடைய திட்டங்கள்:\n\n"
                tail = "\nதிட்டத்தின் முழு விவரங்களைப் பார்க்க அதன் பெயரைத் தட்டச்சு செய்யவும் அல்லது இடது பக்கப் பட்டியலில் தேர்ந்தெடுக்கவும்."
                names = [f"• {x['name_ta']}" for x in categories]
            elif lang == "Tanglish":
                header = "Ungal kelvikku porundhak koodiya schemes:\n\n"
                tail = "\nFull details paarkka scheme name-ai type pannunga alladhu left side list-la select pannunga."
                names = ["• " + TANGLISH_SCHEME_NAMES.get(x["id"], x["name_en"]) for x in categories]
            else:
                header = "Schemes that may be relevant to your request:\n\n"
                tail = "\nType a scheme name or select one from the left panel to see the full details."
                names = [f"• {x['name_en']}" for x in categories]
            return header + "\n".join(names) + tail, None
        if lang == "Tamil":
            return ("இந்தக் கேள்விக்கான திட்டம் உள்ளூர் தரவுத்தளத்தில் கிடைக்கவில்லை. திட்டத்தின் பெயரைச் சரியாகத் தட்டச்சு செய்யவும் அல்லது ‘திட்டங்களின் பட்டியல்’ என்று கேட்கவும். சமீபத்திய தகவலுக்கு அதிகாரப்பூர்வ அரசு தளத்தைச் சரிபார்க்கவும்.\n\nஅனைத்து சேவைகள்: https://tnesevai.tn.gov.in/Pages/ServiceList.aspx", None)
        if lang == "Tanglish":
            return ("Indha kelvikkaana scheme local database-la kidaikkavillai. Scheme name-ai sariyaa type pannunga alladhu 'list schemes' nu kelunga. Latest details-ku official government website-ai check pannunga.\n\nhttps://tnesevai.tn.gov.in/Pages/ServiceList.aspx", None)
        return ("I could not identify that scheme in the bundled offline database. Try the exact scheme name or ask 'list schemes'. I will not invent eligibility or document requirements. For broader official service listings, check Tamil Nadu e-Sevai: https://tnesevai.tn.gov.in/Pages/ServiceList.aspx", None)

    def greeting(self, lang: str) -> str:
        en = "Vanakkam! I'm Rural Scheme AI, an offline guide to selected Tamil Nadu and central government schemes. Ask in Tamil, English, or Tanglish. I can explain benefits, eligibility, documents and application steps from the local scheme database."
        ta = "வணக்கம்! நான் நம்ம திட்டம் AI. தமிழ்நாடு மற்றும் மத்திய அரசின் தேர்ந்தெடுக்கப்பட்ட திட்டங்களைப் பற்றிய ஆஃப்லைன் வழிகாட்டி. தமிழ், ஆங்கிலம் அல்லது Tanglish-ல் கேட்கலாம். திட்ட நன்மைகள், தகுதி, தேவையான ஆவணங்கள் மற்றும் விண்ணப்பிக்கும் முறையை விளக்குகிறேன்."
        if lang == "Tamil": return ta
        if lang == "Tanglish":
            return "Vanakkam! Naan Rural Scheme AI. Tamil Nadu matrum maththiya arasin sila government schemes patri offline-la guide seiven. Tamil, English alladhu Tanglish-la kelunga. Benefits, eligibility, required documents matrum eppadi apply pannalaam enbadhai local database-la irukkum details-ai base panni explain seiven."
        return en

    def list_schemes(self, lang: str) -> str:
        if lang == "Tamil":
            return "உள்ளூர் தரவுத்தளத்தில் உள்ள திட்டங்கள்:\n\n" + "\n".join("• " + s["name_ta"] for s in self.schemes) + "\n\nவிவரங்களைப் பெற திட்டத்தின் பெயரைத் தட்டச்சு செய்யவும்."
        if lang == "Tanglish":
            return "Local database-la irukkira schemes:\n\n" + "\n".join("• " + TANGLISH_SCHEME_NAMES.get(s["id"], s["name_en"]) for s in self.schemes) + "\n\nFull details venumna scheme name-ai type pannunga."
        return "Schemes in the bundled local database:\n\n" + "\n".join("• " + s["name_en"] for s in self.schemes) + "\n\nType a scheme name to get its full details."


class NammaThittamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1250x820")
        self.minsize(980, 650)
        self.configure(bg=BG)
        try:
            self.schemes = load_schemes()
        except Exception as exc:
            logging.exception("Application initialization failed")
            messagebox.showerror(APP_NAME, str(exc))
            self.destroy()
            return
        self.assistant = SchemeAssistant(self.schemes)
        self.lang_var = tk.StringVar(value="English")
        self.voice_lang_var = tk.StringVar(value="Auto / selected language")
        self.auto_speak_var = tk.BooleanVar(value=True)
        # Prefer more natural neural voices when the user has internet access.
        self.natural_voice_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Offline mode · No API keys · Local scheme database")
        self.voice_model = None
        self.loaded_voice_model_size = None
        self.voice_model_size = "base"  # tiny=fast, base=balanced, small=better accuracy
        self.voice_device_id = None     # None means use the Windows/system default input
        self.voice_stop_event = threading.Event()
        self.voice_loading = False
        self.recording = False
        self.voice_button = None
        self.tts_lock = threading.Lock()
        self.tts_stop_event = threading.Event()
        self.tts_engine = None
        self.active_scheme = None
        self.last_query_for_language = ""
        self.sidebar_visible = True
        self._message_labels: list[tuple[tk.Label, bool]] = []
        self.history = ChatHistoryStore(DB_FILE)
        self._style()
        self._build_ui()
        self.restore_history()
        if not self.chat_inner.winfo_children():
            self.add_message("assistant", self.assistant.greeting(self.lang_var.get()))

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXT,
                        arrowcolor=TEXT, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXT)])
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG,
                        bordercolor=BG, arrowcolor=TEXT, relief="flat", width=10)
        style.map("Vertical.TScrollbar", background=[("active", PANEL_2), ("pressed", GREEN)])

    def _build_ui(self):
        """Build the native desktop layout: fixed sidebar controls + independently scrollable lists/chat."""
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left sidebar. Its controls remain fixed while the scheme list scrolls.
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=292)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(4, weight=1)

        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.grid(row=0, column=0, sticky="ew", padx=17, pady=(18, 13))
        tk.Label(brand, text="●", fg=GREEN, bg=SIDEBAR,
                 font=("Segoe UI", 23, "bold")).pack(side="left", padx=(0, 9))
        brand_text = tk.Frame(brand, bg=SIDEBAR)
        brand_text.pack(side="left", fill="x", expand=True)
        tk.Label(brand_text, text="Rural Scheme", fg=TEXT, bg=SIDEBAR,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(brand_text, text="LOCAL SCHEME ASSISTANT", fg=MUTED, bg=SIDEBAR,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        self._button(self.sidebar, "＋  New chat", self.new_chat, fill=True).grid(
            row=1, column=0, sticky="ew", padx=15, pady=(0, 13)
        )

        language_panel = tk.Frame(self.sidebar, bg=SIDEBAR)
        language_panel.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        tk.Label(language_panel, text="LANGUAGE / மொழி", fg=MUTED, bg=SIDEBAR,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.language_combo = ttk.Combobox(
            language_panel, textvariable=self.lang_var,
            values=["English", "Tamil", "Tanglish"], state="readonly"
        )
        self.language_combo.pack(fill="x")
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        search_panel = tk.Frame(self.sidebar, bg=SIDEBAR)
        search_panel.grid(row=3, column=0, sticky="ew", padx=16, pady=(1, 7))
        title_row = tk.Frame(search_panel, bg=SIDEBAR)
        title_row.pack(fill="x", pady=(0, 6))
        tk.Label(title_row, text="SCHEME DATABASE", fg=MUTED, bg=SIDEBAR,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.scheme_count_var = tk.StringVar(value=f"{len(self.schemes)} schemes")
        tk.Label(title_row, textvariable=self.scheme_count_var, fg=MUTED, bg=SIDEBAR,
                 font=("Segoe UI", 8)).pack(side="right")
        self.scheme_search_var = tk.StringVar()
        search_row = tk.Frame(search_panel, bg=SIDEBAR)
        search_row.pack(fill="x")
        self.scheme_search_entry = tk.Entry(
            search_row, textvariable=self.scheme_search_var, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=GREEN
        )
        self.scheme_search_entry.pack(fill="x", ipady=9)
        self.scheme_search_entry.insert(0, "Find a scheme...")
        self.scheme_search_entry.bind("<FocusIn>", self._clear_scheme_placeholder)
        self.scheme_search_entry.bind("<KeyRelease>", self.filter_scheme_buttons)
        self.scheme_search_entry.bind("<Escape>", self._clear_scheme_search)

        scheme_scroll = ScrollableFrame(self.sidebar, background=SIDEBAR, canvas_background=SIDEBAR)
        scheme_scroll.grid(row=4, column=0, sticky="nsew", padx=(8, 5), pady=(0, 8))
        self.scheme_scrollable = scheme_scroll
        self.scheme_canvas = scheme_scroll.canvas
        self.scheme_buttons_frame = scheme_scroll.content
        self.scheme_buttons: list[tuple[dict, tk.Button]] = []

        footer = tk.Frame(self.sidebar, bg=SIDEBAR)
        footer.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 13))
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x", pady=(0, 8))
        tk.Label(footer, text="●  NO API KEYS  ·  LOCAL DATA", fg=GREEN, bg=SIDEBAR,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(footer, text="Verify current rules with official sources.", fg=MUTED,
                 bg=SIDEBAR, font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=(3, 0))

        # Main conversation pane.
        main = tk.Frame(self, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)
        self.main_panel = main

        header = tk.Frame(main, bg=SIDEBAR, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        self._button(header, "☰", self.toggle_sidebar, compact=True).pack(
            side="left", padx=(10, 5), pady=18
        )
        avatar = tk.Label(header, text="NT", fg=TEXT, bg=GREEN,
                          font=("Segoe UI", 11, "bold"), width=4, height=2)
        avatar.pack(side="left", padx=(5, 10), pady=12)
        header_text = tk.Frame(header, bg=SIDEBAR)
        header_text.pack(side="left", pady=12, fill="x", expand=True)
        tk.Label(header_text, text="Rural Scheme AI", fg=TEXT, bg=SIDEBAR,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(header_text, text="Government scheme guide · Desktop app · No API keys",
                 fg=MUTED, bg=SIDEBAR, font=("Segoe UI", 9)).pack(anchor="w")
        self._button(header, "🔊 Speak", self.speak_last, compact=True).pack(
            side="right", padx=(4, 12), pady=18
        )
        self._button(header, "■ Stop speech", self.stop_speech, compact=True).pack(
            side="right", padx=4, pady=18
        )
        self._button(header, "⚙ Voice", self.open_voice_settings, compact=True).pack(
            side="right", padx=4, pady=18
        )
        self.voice_button = self._button(header, "🎙 Voice", self.start_voice, compact=True)
        self.voice_button.pack(side="right", padx=4, pady=18)

        # Chat scroll area.
        chat_wrap = tk.Frame(main, bg=BG)
        chat_wrap.grid(row=1, column=0, sticky="nsew")
        chat_wrap.rowconfigure(0, weight=1)
        chat_wrap.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(chat_wrap, bg=BG, highlightthickness=0, borderwidth=0)
        self.chat_scrollbar = ttk.Scrollbar(chat_wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.chat_scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.chat_scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_inner = tk.Frame(self.canvas, bg=BG)
        self.inner_window = self.canvas.create_window((0, 0), window=self.chat_inner, anchor="nw")
        self.chat_inner.bind("<Configure>", self._on_chat_configure, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

        suggestions = tk.Frame(main, bg=BG)
        suggestions.grid(row=2, column=0, sticky="ew", padx=18, pady=(4, 0))
        for label, query in [
            ("Farmer schemes", "show schemes for farmers"),
            ("Student schemes", "student schemes"),
            ("Pension", "old age pension"),
            ("All schemes", "list schemes"),
        ]:
            self._button(suggestions, label, lambda q=query: self.send_query(q), compact=True).pack(
                side="left", padx=(0, 7), pady=5
            )

        composer_wrap = tk.Frame(main, bg=BG)
        composer_wrap.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 10))
        composer_wrap.columnconfigure(0, weight=1)
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            composer_wrap, textvariable=self.input_var, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 11),
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=GREEN
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", ipady=13, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda _event: self.send_current())
        self.input_entry.insert(0, "Ask about any government scheme...")
        self.input_entry.bind("<FocusIn>", self._clear_input_placeholder)
        self._button(composer_wrap, "➤ Send", self.send_current, fill=True).grid(
            row=0, column=1, sticky="ns"
        )

        speak_row = tk.Frame(main, bg=BG)
        speak_row.grid(row=4, column=0, sticky="ew", padx=19, pady=(0, 9))
        tk.Checkbutton(
            speak_row, text="Speak replies aloud", variable=self.auto_speak_var,
            bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG,
            activeforeground=TEXT, font=("Segoe UI", 9)
        ).pack(side="left")
        tk.Checkbutton(
            speak_row, text="Natural voice (internet)", variable=self.natural_voice_var,
            bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG,
            activeforeground=TEXT, font=("Segoe UI", 9)
        ).pack(side="left", padx=(10, 0))
        tk.Label(speak_row, textvariable=self.status_var, fg=MUTED, bg=BG,
                 font=("Segoe UI", 8), anchor="e").pack(side="right", fill="x", expand=True, padx=(8, 0))

        # Bind wheel events once. The handler scrolls whichever pane is under the pointer.
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_linux_wheel_up, add="+")
        self.bind_all("<Button-5>", self._on_linux_wheel_down, add="+")
        self._render_scheme_buttons()

    def _button(self, parent, text, command, fill=False, compact=False):
        return tk.Button(
            parent, text=text, command=command,
            bg=GREEN if fill else PANEL, fg=TEXT,
            activebackground=GREEN_HOVER if fill else PANEL_2,
            activeforeground=TEXT, relief="flat", borderwidth=0,
            cursor="hand2", font=("Segoe UI", 9 if compact else 10, "bold" if fill else "normal"),
            padx=10 if compact else 13, pady=7 if compact else 9,
            takefocus=True,
        )

    def toggle_sidebar(self):
        """Collapse/restore the left sidebar without rebuilding the chat area."""
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
        else:
            self.sidebar.grid()
            self.sidebar_visible = True

    def _clear_scheme_placeholder(self, _event=None):
        if self.scheme_search_entry.get() == "Find a scheme...":
            self.scheme_search_entry.delete(0, "end")

    def _clear_scheme_search(self, _event=None):
        self.scheme_search_entry.delete(0, "end")
        self.filter_scheme_buttons()
        return "break"

    def _clear_input_placeholder(self, _event=None):
        if self.input_entry.get() == "Ask about any government scheme...":
            self.input_entry.delete(0, "end")

    def _on_chat_configure(self, _event=None):
        # Update geometry only; don't force-scroll when a user is reading older messages.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.inner_window, width=max(1, event.width))
        self._update_message_wrap_lengths()

    @staticmethod
    def _is_descendant(widget, ancestor) -> bool:
        """Return True when widget is ancestor or nested below it."""
        node = widget
        while node is not None:
            if node == ancestor:
                return True
            node = getattr(node, "master", None)
        return False

    def _canvas_under_pointer(self, event):
        try:
            target = self.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, AttributeError):
            return None
        if target is not None and self._is_descendant(target, self.scheme_canvas):
            return self.scheme_canvas
        if target is not None and self._is_descendant(target, self.canvas):
            return self.canvas
        return None

    def _scroll_at_pointer(self, event, direction=None):
        canvas = self._canvas_under_pointer(event)
        if canvas is None:
            return
        if direction is not None:
            units = direction
        else:
            delta = getattr(event, "delta", 0)
            if not delta:
                return
            # Windows uses multiples of 120; some touchpads send smaller deltas.
            units = -int(delta / 120)
            if units == 0:
                units = -1 if delta > 0 else 1
        canvas.yview_scroll(units, "units")
        return "break"

    def _on_mousewheel(self, event):
        return self._scroll_at_pointer(event)

    def _on_linux_wheel_up(self, event):
        return self._scroll_at_pointer(event, direction=-1)

    def _on_linux_wheel_down(self, event):
        return self._scroll_at_pointer(event, direction=1)

    def _scroll_chat_to_bottom(self):
        try:
            self.canvas.yview_moveto(1.0)
        except tk.TclError:
            pass

    def _update_message_wrap_lengths(self):
        width = max(420, self.canvas.winfo_width())
        assistant_wrap = max(280, min(850, int((width - 70) * 0.78)))
        user_wrap = max(230, min(650, int((width - 80) * 0.62)))
        for label, is_user in tuple(self._message_labels):
            try:
                if label.winfo_exists():
                    label.configure(wraplength=user_wrap if is_user else assistant_wrap)
            except tk.TclError:
                continue

    def filter_scheme_buttons(self, _event=None):
        # Rebuild the small list in its original data order so filtering never reorders items.
        self._render_scheme_buttons()

    def _render_scheme_buttons(self):
        query = self.scheme_search_var.get().casefold().strip()
        if query == "find a scheme...":
            query = ""
        tokens = normalise(query).split()
        for child in self.scheme_buttons_frame.winfo_children():
            child.destroy()
        self.scheme_buttons.clear()
        visible = []
        for scheme in self.schemes:
            searchable = " ".join([
                scheme.get("name_en", ""), scheme.get("name_ta", ""),
                TANGLISH_SCHEME_NAMES.get(scheme.get("id", ""), scheme.get("name_en", "")), scheme.get("category", ""),
                " ".join(scheme.get("aliases", [])),
            ])
            haystack = normalise(searchable)
            if all(token in haystack for token in tokens):
                visible.append(scheme)
        self.scheme_count_var.set(f"{len(visible)} / {len(self.schemes)} schemes" if tokens else f"{len(self.schemes)} schemes")
        if not visible:
            tk.Label(self.scheme_buttons_frame, text="No matching schemes found.\nTry Tamil, English or Tanglish.",
                     bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9), justify="left",
                     wraplength=230).pack(fill="x", padx=10, pady=12)
        for scheme in visible:
            if self.lang_var.get() == "Tamil":
                label = scheme.get("name_ta", scheme["name_en"])
            elif self.lang_var.get() == "Tanglish":
                label = TANGLISH_SCHEME_NAMES.get(scheme.get("id", ""), scheme["name_en"])
            else:
                label = scheme["name_en"]
            selected = self.active_scheme and self.active_scheme.get("id") == scheme.get("id")
            button = tk.Button(
                self.scheme_buttons_frame, text="▸  " + label,
                command=lambda item=scheme: self.show_scheme(item),
                bg=PANEL_2 if selected else SIDEBAR, fg=TEXT,
                activebackground=PANEL_2, activeforeground=TEXT,
                relief="flat", borderwidth=0, cursor="hand2",
                font=("Segoe UI", 9), anchor="w", justify="left",
                wraplength=222, padx=11, pady=8, takefocus=True,
            )
            button.pack(fill="x", padx=3, pady=2)
            button.bind("<Enter>", lambda event, b=button: b.configure(bg=PANEL_2))
            button.bind("<Leave>", lambda event, b=button, is_selected=bool(selected):
                        b.configure(bg=PANEL_2 if is_selected else SIDEBAR))
            self.scheme_buttons.append((scheme, button))
        self.scheme_scrollable._update_scroll_region()
        self.scheme_canvas.yview_moveto(0.0)

    def on_language_change(self, _event=None):
        """Apply the selected language immediately to the current answer.

        The last user request is re-answered from the local database, so changing
        English -> Tamil -> Tanglish updates the actual scheme explanation instead
        of changing only the sidebar labels.
        """
        language = self.lang_var.get()
        self.status_var.set(f"Language selected: {language} · No API keys")
        self._render_scheme_buttons()

        query = getattr(self, "last_query_for_language", "").strip()
        if query:
            answer, scheme = self.assistant.answer(query, language)
            self.active_scheme = scheme
        else:
            answer = self.assistant.greeting(language)
            scheme = None
        self.add_message("assistant", answer, scheme)
        if self.auto_speak_var.get():
            self.speak_text(answer, show_errors=False)

    def add_message(self, role: str, text: str, scheme: dict | None = None, save=True, scroll=True):
        outer = tk.Frame(self.chat_inner, bg=BG)
        outer.pack(fill="x", padx=24, pady=(10, 4))
        is_user = role == "user"
        row = tk.Frame(outer, bg=BG)
        row.pack(fill="x")
        bubble_bg = BUBBLE_USER if is_user else BUBBLE_BOT
        bubble = tk.Frame(row, bg=bubble_bg, padx=13, pady=9)
        bubble.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")
        width = max(420, self.canvas.winfo_width())
        wraplength = max(230, min(650, int((width - 80) * 0.62))) if is_user else max(280, min(850, int((width - 70) * 0.78)))
        label = tk.Label(
            bubble, text=text, bg=bubble_bg, fg=TEXT,
            font=("Segoe UI", 10), justify="left", anchor="nw",
            wraplength=wraplength, padx=0, pady=0,
        )
        label.pack(fill="both", expand=True)
        self._message_labels.append((label, is_user))
        stamp = datetime.now().strftime("%I:%M %p")
        tk.Label(
            bubble, text=stamp, bg=bubble_bg,
            fg="#b4cbc5" if is_user else MUTED, font=("Segoe UI", 7)
        ).pack(anchor="e", pady=(4, 0))
        if scheme and not is_user:
            url = scheme.get("official_url", "")
            if url:
                language = self.lang_var.get()
                if language == "Tamil":
                    source_label = "↗ அதிகாரப்பூர்வ இணையதளத்தைத் திறக்கவும்"
                elif language == "Tanglish":
                    source_label = "↗ Official website-ai thirakkavum"
                else:
                    source_label = "↗ Open official source"
                self._button(
                    bubble, source_label,
                    lambda u=url: webbrowser.open(u), compact=True
                ).pack(anchor="w", pady=(8, 0))
        if save:
            try:
                self.history.save(role, text, self.lang_var.get(), scheme.get("id") if scheme else None)
            except (sqlite3.Error, RuntimeError):
                logging.exception("Unable to save chat history")
                self.status_var.set("Message shown, but chat history could not be saved.")
        if scroll:
            self.canvas.after_idle(self._scroll_chat_to_bottom)
        if role == "assistant":
            self.last_response = text

    def restore_history(self):
        try:
            rows = self.history.recent(limit=16)
            for role, text, scheme_id in rows:
                scheme = self.assistant.by_id.get(scheme_id) if scheme_id else None
                self.add_message(role, text, scheme, save=False, scroll=False)
            if rows:
                self.canvas.after_idle(self._scroll_chat_to_bottom)
        except (sqlite3.Error, tk.TclError):
            logging.exception("Unable to restore chat history")
            self.status_var.set("Chat history could not be restored; you can start a new chat.")

    def new_chat(self):
        for child in self.chat_inner.winfo_children():
            child.destroy()
        self._message_labels.clear()
        try:
            self.history.clear()
        except sqlite3.Error:
            logging.exception("Unable to clear chat history")
            self.status_var.set("Could not clear saved history.")
        self.active_scheme = None
        self.last_query_for_language = ""
        self._render_scheme_buttons()
        self.add_message("assistant", self.assistant.greeting(self.lang_var.get()))
        self.input_entry.focus_set()

    def show_scheme(self, scheme):
        self.active_scheme = scheme
        self.last_query_for_language = scheme.get("name_en", scheme.get("id", ""))
        self._render_scheme_buttons()
        language = self.lang_var.get()
        response = self.assistant.format_scheme(scheme, language)
        if language == "Tamil":
            user_text = scheme.get("name_ta", scheme["name_en"])
        elif language == "Tanglish":
            user_text = TANGLISH_SCHEME_NAMES.get(scheme.get("id", ""), scheme["name_en"])
        else:
            user_text = scheme["name_en"]
        self.add_message("user", user_text)
        self.add_message("assistant", response, scheme)
        if self.auto_speak_var.get():
            self.speak_text(response, show_errors=False)

    def send_current(self):
        query = self.input_var.get().strip()
        if not query or query == "Ask about any government scheme...": return
        self.input_var.set("")
        self.send_query(query)

    def send_query(self, query: str):
        self.last_query_for_language = query
        self.add_message("user", query)
        language = self.lang_var.get()
        answer, scheme = self.assistant.answer(query, language)
        self.active_scheme = scheme
        self.add_message("assistant", answer, scheme)
        if self.auto_speak_var.get():
            spoken_answer = answer
            # Keep the on-screen related-scheme suggestions, but do not make Tamil
            # voice read every scheme name aloud. Invite the user to choose one;
            # selecting it calls show_scheme(), which speaks the full explanation.
            if scheme is None and language == "Tamil" and answer.startswith("உங்கள் கேள்விக்கு தொடர்புடைய திட்டங்கள்:"):
                spoken_answer = (
                    "உங்கள் கேள்விக்கு தொடர்புடைய திட்டங்கள் திரையில் காட்டப்பட்டுள்ளன. "
                    "ஒரு திட்டத்தின் முழு விவரங்களை அறிய, இடது பக்கப் பட்டியலில் அந்தத் திட்டத்தைத் தேர்ந்தெடுக்கவும். "
                    "அப்போது அதன் நன்மைகள், தகுதி, தேவையான ஆவணங்கள் மற்றும் விண்ணப்பிக்கும் முறையை விளக்குகிறேன்."
                )
            self.speak_text(spoken_answer, show_errors=False)

    def stop_speech(self):
        """Immediately request that either natural or local text-to-speech stop."""
        self.tts_stop_event.set()
        try:
            engine = self.tts_engine
            if engine is not None:
                engine.stop()
        except Exception:
            logging.exception("Could not stop local speech engine")
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            # pygame may not be installed or initialized; local TTS stop still applies.
            pass
        self.status_var.set("Stopping speech…")

    def speak_last(self):
        text = getattr(self, "last_response", "")
        if not text:
            self.status_var.set("No reply to speak yet.")
            return
        self.speak_text(text, show_errors=True)

    def speak_text(self, text: str, show_errors: bool):
        """Speak in the selected language; prefer natural neural voices, then local TTS."""
        selected_language = self.lang_var.get()
        self.tts_stop_event.clear()
        spoken_text = speech_safe_text(text, selected_language)
        if not spoken_text:
            self.status_var.set("There is no readable answer text to speak.")
            return

        def voice_languages(voice):
            parts = [str(getattr(voice, "name", "")), str(getattr(voice, "id", ""))]
            for raw in (getattr(voice, "languages", []) or []):
                try:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="ignore")
                    parts.append(str(raw))
                except Exception:
                    continue
            return " ".join(parts).casefold()

        def try_natural_voice() -> bool:
            """Use Edge neural speech if installed; this requires internet, not an API key."""
            import asyncio
            import edge_tts
            import pygame

            if selected_language == "Tamil":
                voice_name = "ta-IN-PallaviNeural"
            elif selected_language == "Tanglish":
                voice_name = "en-IN-NeerjaNeural"
            else:
                voice_name = "en-IN-NeerjaNeural"

            fd, audio_path = tempfile.mkstemp(prefix="namma_thittam_voice_", suffix=".mp3")
            os.close(fd)
            try:
                async def create_audio():
                    communicate = edge_tts.Communicate(
                        spoken_text, voice=voice_name, rate="-5%", volume="+0%"
                    )
                    await communicate.save(audio_path)

                asyncio.run(create_audio())
                # pygame handles MP3 playback on Windows; the worker keeps the GUI responsive.
                with self.tts_lock:
                    pygame.mixer.init()
                    try:
                        pygame.mixer.music.load(audio_path)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and not self.tts_stop_event.is_set():
                            time.sleep(0.10)
                        if self.tts_stop_event.is_set():
                            pygame.mixer.music.stop()
                            return True
                        pygame.mixer.music.stop()
                    finally:
                        pygame.mixer.quit()
                return True
            finally:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

        def worker():
            # Tamil must use the Tamil neural voice even if the optional
            # "Natural voice" checkbox has been turned off. Otherwise Windows
            # may try to read Tamil-script text with an English system voice.
            use_natural_voice = (selected_language == "Tamil") or self.natural_voice_var.get()
            if use_natural_voice and not self.tts_stop_event.is_set():
                try:
                    if try_natural_voice():
                        if not self.tts_stop_event.is_set():
                            message = ("Tamil neural voice finished" if selected_language == "Tamil"
                                       else "Natural neural voice finished · Indian English")
                            self.after(0, lambda msg=message: self.status_var.set(msg))
                        return
                except Exception as exc:
                    if self.tts_stop_event.is_set():
                        return
                    logging.info("Natural TTS unavailable; falling back to local voice: %s", exc)
                    fallback_message = (
                        "Tamil online voice unavailable; checking for a Windows Tamil voice…"
                        if selected_language == "Tamil"
                        else "Natural voice unavailable; trying installed local voice…"
                    )
                    self.after(0, lambda msg=fallback_message: self.status_var.set(msg))

            try:
                import pyttsx3
            except ImportError:
                self.after(0, lambda: self.status_var.set(
                    "Install speech support: python -m pip install pyttsx3 edge-tts pygame"
                ))
                if show_errors:
                    self.after(0, lambda: messagebox.showinfo(
                        "Voice support",
                        "Install speech support with:\npython -m pip install pyttsx3 edge-tts pygame"
                    ))
                return
            try:
                with self.tts_lock:
                    if self.tts_stop_event.is_set():
                        return
                    engine = pyttsx3.init()
                    self.tts_engine = engine
                    voices = engine.getProperty("voices") or []
                    selected_voice = None
                    if selected_language == "Tamil":
                        # Only use a real Tamil system voice for Tamil-script text.
                        for voice in voices:
                            info = voice_languages(voice)
                            if any(token in info for token in ("tamil", "ta-in", "ta_in", "tain", "0449")):
                                selected_voice = voice
                                break
                        if selected_voice is None:
                            engine.stop()
                            self.after(0, lambda: self.status_var.set(
                                "Tamil neural voice needs internet; local Tamil voice is not installed."
                            ))
                            if show_errors:
                                self.after(0, lambda: messagebox.showinfo(
                                    "Tamil voice unavailable",
                                    "Natural Tamil speech needs internet and the optional edge-tts/pygame packages.\n\n"
                                    "Install them with: python -m pip install edge-tts pygame\n"
                                    "Or install a Tamil speech voice in Windows Settings → Time & language → Speech."
                                ))
                            return
                    else:
                        # Prefer Indian English rather than the first arbitrary system voice.
                        for voice in voices:
                            info = voice_languages(voice)
                            if any(token in info for token in ("en-in", "english india", "indian english")):
                                selected_voice = voice
                                break
                        if selected_voice is None:
                            for voice in voices:
                                if "english" in voice_languages(voice) or "en-us" in voice_languages(voice):
                                    selected_voice = voice
                                    break
                        if selected_voice is None and voices:
                            selected_voice = voices[0]
                    if selected_voice is not None:
                        engine.setProperty("voice", selected_voice.id)
                    engine.setProperty("rate", 138 if selected_language == "Tamil" else 148)
                    engine.setProperty("volume", 1.0)
                    if not self.tts_stop_event.is_set():
                        engine.say(spoken_text)
                        engine.runAndWait()
                    engine.stop()
                    self.tts_engine = None
                if self.tts_stop_event.is_set():
                    self.after(0, lambda: self.status_var.set("Speech stopped."))
                else:
                    self.after(0, lambda: self.status_var.set("Voice reply finished · Local TTS"))
            except Exception as exc:
                logging.exception("Voice output failed")
                self.after(0, lambda msg=str(exc): self.status_var.set("Voice output unavailable: " + msg[:100]))
                if show_errors:
                    self.after(0, lambda msg=str(exc): messagebox.showerror("Voice output error", msg[:1200]))
        threading.Thread(target=worker, daemon=True, name="text-to-speech-worker").start()

    def _voice_status(self, message: str):
        """Safely update the status bar from the voice worker thread."""
        try:
            self.after(0, lambda msg=message: self.status_var.set(msg))
        except tk.TclError:
            pass

    def _voice_problem(self, title: str, message: str, status: str):
        """Show a useful voice error instead of leaving details only in a log."""
        def show():
            try:
                self.status_var.set(status)
                messagebox.showerror(title, message, parent=self)
            except tk.TclError:
                pass
        try:
            self.after(0, show)
        except tk.TclError:
            pass

    def _set_voice_button(self, text: str, enabled: bool = True):
        """Change the voice button only on Tk's event loop."""
        def update():
            try:
                if self.voice_button and self.voice_button.winfo_exists():
                    self.voice_button.configure(text=text, state="normal" if enabled else "disabled")
            except tk.TclError:
                pass
        try:
            self.after(0, update)
        except tk.TclError:
            pass

    def open_voice_settings(self):
        """Let the user choose a real microphone and recognition accuracy locally."""
        if self.recording or self.voice_loading:
            messagebox.showinfo(
                "Voice is busy",
                "Finish the current recording or wait for recognition to complete before changing microphone/model settings.",
                parent=self,
            )
            return
        try:
            import sounddevice as sd
            devices = sd.query_devices()
        except ImportError:
            messagebox.showinfo(
                "Voice settings",
                "Install voice recognition packages first:\n\npython -m pip install -r requirements.txt",
                parent=self,
            )
            return
        except Exception as exc:
            logging.exception("Unable to query microphone devices")
            messagebox.showerror(
                "Microphone settings",
                "Windows could not list microphone devices. Check that a microphone is connected.\n\n" + str(exc),
                parent=self,
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Voice recognition settings")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        frame = tk.Frame(dialog, bg=BG, padx=20, pady=18)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Voice recognition settings", bg=BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 14))

        tk.Label(frame, text="Microphone input", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        device_labels = ["System default microphone"]
        device_map = {"System default microphone": None}
        for idx, device in enumerate(devices):
            inputs = int(device.get("max_input_channels", 0) or 0)
            if inputs > 0:
                label = f"{idx}: {device.get('name', 'Microphone')} ({inputs} input channel(s))"
                device_labels.append(label)
                device_map[label] = idx
        current_label = "System default microphone"
        if self.voice_device_id is not None:
            for label, idx in device_map.items():
                if idx == self.voice_device_id:
                    current_label = label
                    break
        device_var = tk.StringVar(value=current_label)
        device_combo = ttk.Combobox(frame, textvariable=device_var, values=device_labels,
                                    state="readonly", width=48)
        device_combo.pack(fill="x", pady=(5, 14))

        tk.Label(frame, text="Recognition model", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        model_options = {
            "Fast · tiny (lower accuracy)": "tiny",
            "Balanced · base (recommended)": "base",
            "More accurate · small (slower, bigger download)": "small",
        }
        reverse_models = {value: label for label, value in model_options.items()}
        model_var = tk.StringVar(value=reverse_models.get(self.voice_model_size, reverse_models["base"]))
        model_combo = ttk.Combobox(frame, textvariable=model_var, values=list(model_options),
                                   state="readonly", width=48)
        model_combo.pack(fill="x", pady=(5, 8))
        tk.Label(
            frame,
            text="The first time you use a model, it may need a one-time download. After it is cached, recognition is local and needs no API key.",
            bg=BG, fg=MUTED, justify="left", wraplength=390,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 16))

        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x")

        def save_settings():
            new_device = device_map.get(device_var.get())
            new_model = model_options.get(model_var.get(), "base")
            model_changed = new_model != self.voice_model_size
            self.voice_device_id = new_device
            if model_changed:
                self.voice_model = None
                self.loaded_voice_model_size = None
                self.voice_model_size = new_model
            device_name = device_var.get().split(":", 1)[-1].strip() if new_device is not None else "system default"
            message = f"Voice settings saved · {new_model} model · {device_name}"
            self.status_var.set(message)
            dialog.destroy()

        self._button(buttons, "Cancel", dialog.destroy, compact=True).pack(side="right", padx=(6, 0))
        self._button(buttons, "Save settings", save_settings, fill=True).pack(side="right")
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(10, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(10, (self.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def start_voice(self):
        """Toggle local voice capture. Tap Voice to start and Stop to finish early.

        Recording streams in short chunks, stops after a pause in speech, and has
        a maximum duration. Model loading/transcription stays off the GUI thread.
        """
        if self.recording:
            self.voice_stop_event.set()
            self.status_var.set("Stopping microphone and processing what you said…")
            self._set_voice_button("⏳ Processing…", enabled=False)
            return
        if self.voice_loading:
            self.status_var.set("Your speech is being recognized locally. Please wait…")
            return
        self.voice_stop_event.clear()
        self.recording = True
        self.voice_loading = False
        selected_language = self.lang_var.get()
        self.status_var.set("Starting microphone…")
        self._set_voice_button("■ Stop voice", enabled=True)
        threading.Thread(
            target=self._record_and_transcribe,
            args=(selected_language,),
            daemon=True,
            name="offline-speech-recognition",
        ).start()

    def _record_and_transcribe(self, selected_language: str):
        phase = "checking voice packages"
        try:
            try:
                import numpy as np
                import sounddevice as sd
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "Voice input packages are missing. Open Command Prompt in the app folder and run:\n\n"
                    "python -m pip install -r requirements.txt\n\n"
                    "Or install them with:\npython -m pip install faster-whisper sounddevice numpy"
                ) from exc

            phase = "checking microphone"
            try:
                devices = sd.query_devices()
            except Exception as exc:
                raise RuntimeError(
                    "Windows could not list audio devices. Restart the app and check that an input microphone is connected.\n\n"
                    f"Audio system detail: {exc}"
                ) from exc

            input_device = self.voice_device_id
            if input_device is None:
                try:
                    default_devices = sd.default.device
                    if isinstance(default_devices, (tuple, list)) and default_devices:
                        input_device = default_devices[0]
                    elif default_devices is not None:
                        input_device = default_devices
                    if input_device is not None and int(input_device) < 0:
                        input_device = None
                except Exception:
                    input_device = None
            if input_device is None:
                for idx, device in enumerate(devices):
                    if int(device.get("max_input_channels", 0) or 0) > 0:
                        input_device = idx
                        break
            if input_device is None:
                raise RuntimeError(
                    "No microphone input device was found. Connect a microphone or open Windows Settings → System → Sound → Input."
                )

            device_info = sd.query_devices(int(input_device))
            if int(device_info.get("max_input_channels", 0) or 0) < 1:
                raise RuntimeError(
                    f'The selected audio device "{device_info.get("name", "Unknown device")}" has no input channels. '
                    "Open ⚙ Voice and select a microphone with input channels."
                )

            # Pick a sample rate the actual device accepts; devices vary across PCs.
            preferred_rate = int(round(float(device_info.get("default_samplerate") or 44100)))
            candidate_rates = []
            for rate in (preferred_rate, 48000, 44100, 32000, 22050, 16000):
                if rate >= 8000 and rate not in candidate_rates:
                    candidate_rates.append(rate)
            source_rate = None
            for rate in candidate_rates:
                try:
                    sd.check_input_settings(device=int(input_device), samplerate=rate, channels=1, dtype="float32")
                    source_rate = rate
                    break
                except Exception:
                    continue
            if source_rate is None:
                raise RuntimeError(
                    f'Could not find a supported sample rate for "{device_info.get("name", "microphone")}". '
                    "Choose another microphone in ⚙ Voice or check the Windows input device settings."
                )

            # Stream 100ms frames, so the recording can be stopped by button and
            # ends shortly after speech pauses. This is friendlier than a fixed 8s.
            max_seconds = 40
            no_speech_timeout = 12
            silence_timeout = 1.8
            chunk_frames = max(800, int(source_rate * 0.10))
            audio_chunks = []
            noise_samples = []
            speech_started = False
            last_voice_time = None
            capture_start = time.monotonic()
            latest_status_time = capture_start
            phase = "recording from microphone"
            self._voice_status(
                f'Listening on "{device_info.get("name", "microphone")}". Speak naturally; click Stop voice to finish.'
            )

            try:
                with sd.InputStream(
                    samplerate=source_rate, channels=1, dtype="float32",
                    blocksize=chunk_frames, device=int(input_device),
                ) as stream:
                    while not self.voice_stop_event.is_set():
                        elapsed = time.monotonic() - capture_start
                        if elapsed >= max_seconds:
                            self._voice_status("Maximum recording length reached · Recognizing speech…")
                            break
                        data, overflowed = stream.read(chunk_frames)
                        if overflowed:
                            logging.warning("Microphone input overflow while recording voice")
                        chunk = np.asarray(data, dtype=np.float32).reshape(-1)
                        if chunk.size == 0:
                            continue
                        audio_chunks.append(chunk.copy())
                        rms = float(np.sqrt(np.mean(np.square(chunk), dtype=np.float64)))
                        peak = float(np.max(np.abs(chunk)))
                        if not speech_started:
                            # Estimate the ambient noise floor during the first second.
                            # A capped threshold avoids raising the bar too high in a noisy room.
                            if len(noise_samples) < 8:
                                noise_samples.append(rms)
                            noise_floor = float(np.percentile(noise_samples, 40)) if noise_samples else 0.0
                            speech_threshold = max(0.0025, min(0.010, noise_floor * 2.4))
                            active = rms >= speech_threshold or peak >= 0.025
                            if active:
                                speech_started = True
                                last_voice_time = time.monotonic()
                                self._voice_status("Speech detected · Keep speaking, or pause to finish…")
                        else:
                            # Voice activity is intentionally conservative to allow natural pauses.
                            speech_threshold = max(0.0022, min(0.008, (float(np.percentile(noise_samples, 40)) if noise_samples else 0.001) * 2.1))
                            active = rms >= speech_threshold or peak >= 0.022
                            now = time.monotonic()
                            if active:
                                last_voice_time = now
                            elif last_voice_time is not None and now - last_voice_time >= silence_timeout:
                                self._voice_status("Pause detected · Recognizing your speech locally…")
                                break
                        now = time.monotonic()
                        if now - latest_status_time >= 1.0:
                            if not speech_started:
                                self._voice_status(f"Listening… {int(elapsed)}s · Start speaking now")
                            else:
                                self._voice_status(f"Listening… {int(elapsed)}s · Click Stop voice when finished")
                            latest_status_time = now
                        if not speech_started and elapsed >= no_speech_timeout:
                            break
            except Exception as exc:
                raise RuntimeError(
                    "The microphone could not record audio. Open ⚙ Voice to choose an input device, then check Windows Settings → System → Sound → Input and microphone privacy permissions.\n\n"
                    f"Audio detail: {exc}"
                ) from exc

            if not audio_chunks:
                raise RuntimeError("No audio frames were received from the microphone. Check the selected input device and try again.")
            audio = np.concatenate(audio_chunks).astype(np.float32, copy=False)
            duration = audio.size / float(source_rate)
            self.recording = False
            self.voice_loading = True
            self._set_voice_button("⏳ Recognizing…", enabled=False)

            if not speech_started:
                self._voice_problem(
                    "No speech detected",
                    "The microphone opened, but the recording did not contain clear speech.\n\n"
                    "• Open ⚙ Voice and choose the microphone whose input meter responds.\n"
                    "• Check Windows Settings → System → Sound → Input and microphone privacy permissions.\n"
                    "• Click Voice and speak after the status says Listening. Keep the microphone close to you.",
                    "No speech detected · Check microphone and try again",
                )
                return

            rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
            if not np.isfinite(rms) or rms < 0.00012:
                raise RuntimeError("The microphone recording was almost silent. Increase input volume or choose another microphone.")

            # Resample to Whisper's expected 16 kHz mono, locally and without extra dependencies.
            target_rate = 16000
            if source_rate != target_rate:
                target_count = max(1, int(round(audio.size * target_rate / source_rate)))
                old_positions = np.arange(audio.size, dtype=np.float32)
                new_positions = np.linspace(0, audio.size - 1, num=target_count, dtype=np.float32)
                audio = np.interp(new_positions, old_positions, audio).astype(np.float32, copy=False)

            # Improve quiet-mic recordings without clipping loud audio. Whisper works
            # better when speech is audible and the waveform is finite and normalized.
            audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
            peak_level = float(np.max(np.abs(audio))) if audio.size else 0.0
            rms_level = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64))) if audio.size else 0.0
            if peak_level > 0.0 and rms_level < 0.08:
                gain = min(8.0, 0.12 / max(rms_level, 1e-6))
                audio = np.clip(audio * gain, -0.98, 0.98).astype(np.float32, copy=False)

            phase = "loading local speech model"
            if self.voice_model is None or self.loaded_voice_model_size != self.voice_model_size:
                self._voice_status(
                    f"Captured {duration:.1f}s of audio. Loading the local {self.voice_model_size} speech model; first use may download it once…"
                )
                self.voice_model = WhisperModel(self.voice_model_size, device="cpu", compute_type="int8")
                self.loaded_voice_model_size = self.voice_model_size

            phase = "recognizing speech"
            self._voice_status(f"Captured {duration:.1f}s · Recognizing locally ({selected_language})…")
            if selected_language == "Tamil":
                whisper_lang = "ta"
            elif selected_language == "English":
                whisper_lang = "en"
            else:
                # Tanglish is code-switched Tamil/English; auto language detection is usually safer.
                whisper_lang = None
            prompt = (
                "Short spoken command to a Tamil Nadu government scheme assistant. "
                "Recognize the exact words; do not invent or translate the speaker's words. "
                "Common terms: PM Kisan, PMFBY, Pudhumai Penn, Tamil Pudhalvan, "
                "Uzhavar Pathukappu, ration card, pension, scholarship, farmer, Aadhaar, "
                "e-Sevai, apply, benefits, eligibility, documents, how to apply."
            )

            def run_transcription(language_code, use_vad=True):
                segments, info = self.voice_model.transcribe(
                    audio,
                    language=language_code,
                    beam_size=5 if self.voice_model_size != "tiny" else 3,
                    best_of=5 if self.voice_model_size != "tiny" else 3,
                    temperature=0,
                    condition_on_previous_text=False,
                    vad_filter=use_vad,
                    vad_parameters={"min_silence_duration_ms": 450, "speech_pad_ms": 350} if use_vad else None,
                    initial_prompt=prompt,
                    no_speech_threshold=0.5,
                    log_prob_threshold=-1.2,
                    compression_ratio_threshold=2.2,
                )
                # faster-whisper returns a lazy segment iterator; consume it here.
                segment_list = list(segments)
                text = " ".join(segment.text.strip() for segment in segment_list).strip()
                confidence_values = [float(getattr(segment, "avg_logprob", -0.5)) for segment in segment_list]
                avg_logprob = (sum(confidence_values) / len(confidence_values)) if confidence_values else -99.0
                no_speech_values = [float(getattr(segment, "no_speech_prob", 0.0)) for segment in segment_list]
                avg_no_speech = (sum(no_speech_values) / len(no_speech_values)) if no_speech_values else 1.0
                return text, info, avg_logprob, avg_no_speech

            transcript, info, quality, silence_probability = run_transcription(whisper_lang, use_vad=True)
            # Retry difficult short commands with a second decoding pass. Tanglish is
            # code-switched, so auto-detection and disabled VAD can preserve words
            # clipped by the first pass. Use the retry only when quality is weak.
            needs_retry = (
                not transcript
                or len(transcript.split()) <= 2
                or quality < -0.85
                or silence_probability > 0.55
            )
            if needs_retry:
                self._voice_status("Improving recognition · trying a second local pass…")
                retry_language = None if selected_language == "Tanglish" else whisper_lang
                retry_text, retry_info, retry_quality, retry_silence = run_transcription(retry_language, use_vad=False)
                if retry_text and (not transcript or retry_quality > quality):
                    transcript, info, quality, silence_probability = retry_text, retry_info, retry_quality, retry_silence
            transcript = re.sub(r"\s+", " ", transcript).strip(" .,-\t\n")

            # Reject Whisper hallucinations and symbol-heavy/garbled transcripts instead
            # of sending random characters to the chat. This still allows Tamil script,
            # English, numbers, and Tanglish.
            meaningful = re.findall(r"[A-Za-z\u0B80-\u0BFF0-9]+", transcript)
            meaningful_chars = sum(len(token) for token in meaningful)
            total_chars = max(1, len(re.sub(r"\s+", "", transcript)))
            looks_garbled = (
                not meaningful
                or meaningful_chars / total_chars < 0.65
                or re.search(r"(.)\1{5,}", transcript) is not None
            )

            # Remove common Whisper filler/hallucination outputs for empty recordings.
            if transcript.lower() in {"thank you", "thanks for watching", "subscribe", "you", "bye"} and duration < 2.0:
                transcript = ""

            # Low-confidence text recorded mostly during silence is usually a hallucination.
            if looks_garbled or (quality < -1.15 and silence_probability > 0.55):
                logging.warning(
                    "Rejected unreliable voice transcript: quality=%.3f silence=%.3f transcript=%r",
                    quality, silence_probability, transcript
                )
                transcript = ""

            if not transcript:
                self._voice_problem(
                    "Speech not recognized",
                    "Audio was recorded, but the model could not recognize the words.\n\n"
                    "The speech recognizer detected silence or unreliable words, so it did not send them to the AI page. Speak close to the selected microphone and use one clear sentence. In ⚙ Voice, try the 'small' model for better accuracy. Select Tamil for Tamil speech, English for English, or Tanglish for mixed Tamil/English. Reduce background noise and try again. No API key is needed.",
                    "No words recognized · Try again or use a better model",
                )
                return

            detected = getattr(info, "language", None)
            logging.info("Voice recognized: selected=%s detected=%s seconds=%.2f transcript=%r", selected_language, detected, duration, transcript)

            def submit():
                try:
                    self.input_var.set(transcript)
                    self.status_var.set(f"Voice recognized ({detected or selected_language}) · Processing command")
                    self.send_query(transcript)
                except tk.TclError:
                    pass
            self.after(0, submit)

        except Exception as exc:
            logging.exception("Voice input failed during %s", phase)
            detail = str(exc).strip() or repr(exc)
            if phase in ("recording from microphone", "checking microphone"):
                help_text = (
                    "Microphone recording failed. Open ⚙ Voice to choose the input device, then check Windows Settings → System → Sound → Input and microphone privacy permissions.\n\n"
                    "If the error mentions a device or sample rate, try a different input microphone."
                )
            elif phase == "loading local speech model":
                help_text = (
                    "The local speech model could not load. On first use, connect to the internet once so faster-whisper can download/cache the model. No API key is needed. After caching, speech recognition runs locally. If the download failed, check your internet connection and disk space."
                )
            else:
                help_text = "Voice recognition failed. Open ⚙ Voice for microphone/model settings, then try again."
            self._voice_problem(
                "Voice input error",
                help_text + "\n\nTechnical detail:\n" + detail[:1500],
                "Voice input failed · See error details",
            )
        finally:
            self.recording = False
            self.voice_loading = False
            self._set_voice_button("🎙 Voice", enabled=True)

    def destroy(self):
        try:
            self.history.close()
        except Exception:
            logging.exception("Unable to close chat history database")
        super().destroy()


if __name__ == "__main__":
    app = NammaThittamApp()
    app.mainloop()
