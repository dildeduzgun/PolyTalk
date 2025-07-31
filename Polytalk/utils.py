import os
import requests
from io import BytesIO
from sql import db, Kullanici, KullaniciIlerleme, KelimeKart
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import csv
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive 'Agg'
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import re





def create_cards_pdf(kartlar):
    """Kartları PDF formatında oluşturur"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # PDF başlığı
    p.drawString(100, 750, "Kartlarım")
    p.drawString(100, 700, "Bu PDF dosyası kartlarınızı içermektedir.")
    
    # Kartları PDF'e ekle
    y_position = 650
    for kart in kartlar:
        p.drawString(100, y_position, f"Kelime: {kart.kelime}")
        p.drawString(100, y_position - 20, f"Anlam: {kart.anlam}")
        if kart.ornek:
            p.drawString(100, y_position - 40, f"Örnek: {kart.ornek}")
        y_position -= 80
        
        # Sayfa sonuna gelindiğinde yeni sayfa oluştur
        if y_position < 50:
            p.showPage()
            y_position = 750
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

def create_csv(kartlar):
    """Kartları CSV formatında oluşturur"""
    buffer = BytesIO()
    writer = csv.writer(buffer)
    
    # Başlık satırı
    writer.writerow(['Kelime', 'Anlam', 'Örnek', 'Oluşturulma Tarihi'])
    
    # Kartları CSV'e ekle
    for kart in kartlar:
        writer.writerow([
            kart.kelime,
            kart.anlam,
            kart.ornek,
            kart.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    buffer.seek(0)
    return buffer



def create_progress_graphs(ilerleme):
    """Kullanıcının ilerleme grafiklerini oluşturur"""
    plt.figure(figsize=(12, 6))
    sns.set_style("whitegrid")
    
    # XP grafiği
    plt.subplot(1, 2, 1)
    sns.barplot(x=['XP'], y=[ilerleme.toplam_xp])
    plt.title('Toplam XP')
    plt.ylabel('XP')
    
    # Seviye grafiği
    plt.subplot(1, 2, 2)
    plt.pie([ilerleme.seviye, 100 - ilerleme.seviye], labels=['Seviye', 'Kalan'], autopct='%1.1f%%')
    plt.title('Seviye İlerlemesi')
    
    # Grafiği base64'e çevir
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return plot_url



def get_user_stats(user_id):
    """Kullanıcı istatistiklerini hesaplar"""
    ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=user_id).first()
    if not ilerleme:
        ilerleme = KullaniciIlerleme(kullanici_id=user_id, xp=0)
        db.session.add(ilerleme)
        db.session.commit()
    
    stats = {
        'toplam_kelime': KelimeKart.query.filter_by(kullanici_id=user_id).count(),
        'toplam_xp': ilerleme.toplam_xp,
        'mevcut_seviye': ilerleme.seviye,
        'streak': ilerleme.streak
    }
    
    return stats

def get_user_reports(user_id):
    """Kullanıcı raporlarını oluşturur"""
    ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=user_id).first()
    if not ilerleme:
        ilerleme = KullaniciIlerleme(kullanici_id=user_id)
        db.session.add(ilerleme)
        db.session.commit()
    
    plot_url = create_progress_graphs(ilerleme)
    
    stats = {
        'toplam_kelime': KelimeKart.query.filter_by(kullanici_id=user_id).count() or 0,
        'toplam_xp': ilerleme.toplam_xp or 0,
        'mevcut_seviye': ilerleme.seviye or 1,
        'streak': ilerleme.streak or 0
    }
    
    return plot_url, stats

def create_pdf(user_id):
    """Kullanıcı raporunu PDF olarak oluşturur"""
    try:
        plot_url, stats = get_user_reports(user_id)
        user = Kullanici.query.get(user_id)
        
        if not user:
            raise Exception("Kullanıcı bulunamadı")
        
        # PDF dosya yolu
        pdf_path = os.path.join('static', 'reports', f'rapor_{user_id}.pdf')
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # PDF oluştur
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Başlık
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, f"Kullanıcı Raporu: {user.kullanici_adi}")
        
        # İstatistikler
        c.setFont("Helvetica", 12)
        y = 700
        for key, value in stats.items():
            c.drawString(50, y, f"{key}: {value}")
            y -= 20
        
        # Grafik
        if plot_url:
            try:
                img_data = base64.b64decode(plot_url)
                img_path = os.path.join('static', 'reports', f'temp_graph_{user_id}.png')
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                c.drawImage(img_path, 50, y - 200, width=400, height=200)
                # Geçici dosyayı sil
                os.remove(img_path)
            except Exception as e:
                print(f"Grafik eklenirken hata: {e}")
                c.drawString(50, y - 200, "Grafik yüklenemedi")
        
        c.save()
        return pdf_path
    except Exception as e:
        print(f"PDF oluşturulurken hata: {e}")
        raise e

def create_csv(user_id):
    """Kullanıcı verilerini CSV olarak oluşturur"""
    try:
        stats = get_user_stats(user_id)
        user = Kullanici.query.get(user_id)
        
        if not user:
            raise Exception("Kullanıcı bulunamadı")
        
        # CSV dosya yolu
        csv_path = os.path.join('static', 'reports', f'rapor_{user_id}.csv')
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # CSV oluştur
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Kullanıcı Adı', user.kullanici_adi])
            writer.writerow(['Email', user.email])
            writer.writerow([])
            writer.writerow(['İstatistikler'])
            for key, value in stats.items():
                writer.writerow([key, value])
        
        return csv_path
    except Exception as e:
        print(f"CSV oluşturulurken hata: {e}")
        raise e



def calculate_streak(user_id):
    """Kullanıcının streak'ini hesaplar"""
    ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=user_id).first()
    if not ilerleme:
        return 0
    
    today = datetime.utcnow().date()
    last_activity = ilerleme.son_güncelleme.date() if ilerleme.son_güncelleme else None
    
    if not last_activity:
        return 0
    
    if today - last_activity > timedelta(days=1):
        ilerleme.streak = 0
        db.session.commit()
        return 0
    
    return ilerleme.streak

def update_streak(user_id):
    """Kullanıcının streak'ini günceller"""
    ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=user_id).first()
    if not ilerleme:
        ilerleme = KullaniciIlerleme(kullanici_id=user_id, xp=0, streak=1)
        db.session.add(ilerleme)
    else:
        ilerleme.streak += 1
        ilerleme.son_güncelleme = datetime.utcnow()
    
    db.session.commit()
    return ilerleme.streak

def analyze_conversation_for_repetition(conversation_context, user_message):
    """
    Basit tekrar analizi - sadece son birkaç mesajı kontrol eder
    """
    try:
        # Son 30 mesajı analiz et
        lines = conversation_context.split('\n')
        recent_messages = [line.strip() for line in lines if line.strip()][-30:]
        
        # Basit tekrar kontrolü
        user_message_lower = user_message.lower()
        
        # Son bot mesajlarında aynı kelimeler var mı?
        recent_bot_messages = [msg for msg in recent_messages if msg.startswith('Bot:')]
        
        # Basit analiz
        analysis = {
            'total_messages': len(recent_messages),
            'recent_questions': recent_bot_messages[-5:],  # Son 5 bot mesajı
            'has_repeated_question': False,
            'suggested_topics': [],
            'repeated_topics': []
        }
        
        # Çok basit tekrar kontrolü
        if len(recent_bot_messages) > 0:
            last_bot_message = recent_bot_messages[-1].lower()
            # Eğer kullanıcı mesajı çok kısaysa ve bot zaten benzer bir şey sormuşsa
            if len(user_message_lower.split()) <= 3 and any(word in last_bot_message for word in user_message_lower.split()):
                analysis['has_repeated_question'] = True
                analysis['suggested_topics'] = ['details', 'examples', 'reasons']
        
        return analysis
        
    except Exception as e:
        print(f"❌ Basit tekrar analizi hatası: {e}")
        return {
            'total_messages': 0,
            'recent_questions': [],
            'has_repeated_question': False,
            'suggested_topics': [],
            'repeated_topics': []
        }

def generate_chatbot_response(user_message, conversation_context="", topic="general"):
    """
    Generate a contextual chatbot response based on user message and conversation context.
    Uses Gemini API for intelligent, contextual responses.
    """
    try:
        import google.generativeai as genai
        
        # Gemini API anahtarını al
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY bulunamadı!")
            raise Exception("Gemini API anahtarı bulunamadı")
        
        # Gemini'yi yapılandır
        genai.configure(api_key=api_key)
        
        # Model seçimi - daha basit yaklaşım
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            try:
                model = genai.GenerativeModel('gemini-pro')
            except:
                raise Exception("Gemini model yüklenemedi")
        
        # Basit ve etkili prompt oluştur
        if topic == "food":
            system_prompt = """You are a friendly restaurant waiter. Keep responses short (1-2 sentences) and natural. 
            - If customer's order is unclear, ask: "Could you repeat your order?"
            - Ask about size, cooking preference, sides, drinks
            - Don't repeat the same question twice
            - Use simple English for A2 level learners"""
        else:
            system_prompt = """You are a friendly English conversation partner. Keep responses short (1-2 sentences) and natural.
            - If user's message is unclear, ask: "Could you explain what you mean?"
            - Ask follow-up questions about what they said
            - Don't repeat the same question twice
            - Use simple English for A2 level learners
            - Show interest in their specific message"""
        
        # Basit bağlam oluştur
        simple_context = ""
        if conversation_context:
            # Son 30 mesajı al
            lines = conversation_context.split('\n')
            recent_messages = [line for line in lines if line.strip()][-30:]  # Son 30 satır
            simple_context = "\n".join(recent_messages)
        
        # Basit prompt
        prompt = f"""{system_prompt}

Recent conversation:
{simple_context}

User: {user_message}
You:"""
        
        # Gemini API ile yanıt al
        response = model.generate_content(prompt)
        bot_response = response.text.strip()
        
        # Yanıtı temizle ve kısalt
        bot_response = bot_response.replace('You:', '').replace('Bot:', '').strip()
        if len(bot_response) > 150:
            bot_response = bot_response[:150] + "..."
        
        return bot_response
        
    except Exception as e:
        print(f"❌ AI yanıt oluşturma hatası: {e}")
        
        # Basit fallback yanıtlar
        import random
        
        if topic == "food":
            responses = [
                "What size would you like?",
                "How would you like it cooked?",
                "Would you like anything to drink?",
                "Is that for here or to go?",
                "Would you like fries with that?"
            ]
        else:
            responses = [
                "That's interesting! Tell me more.",
                "What do you mean by that?",
                "Could you explain a bit more?",
                "That sounds good! What specifically?",
                "I'd like to understand better. Can you tell me more?"
            ]
        
        return random.choice(responses)

def analyze_chatbot_conversation(chat_history):
    print("DEBUG: chat_history:", chat_history)
    """
    Chatbot sohbetini analiz eder ve kullanıcının kelime hazinesi, 
    gramer hataları ve iyileştirme önerilerini döndürür.
    """
    try:
        print("🔍 AI analizi başlatılıyor...")
        
        # Kullanıcı mesajlarını topla
        user_messages = [msg['text'] for msg in chat_history if msg['role'] == 'user']
        conversation_text = ' '.join(user_messages)
        
        if not conversation_text.strip():
            print("❌ Kullanıcı mesajı bulunamadı")
            return get_fallback_analysis()
        
        print(f"📝 Analiz edilecek metin: {conversation_text[:100]}...")
        
        # Gemini API anahtarını al
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY bulunamadı")
            return get_fallback_analysis()
        
        print(f"✅ API anahtarı bulundu: {api_key[:10]}...")
        
        # Gemini'yi yapılandır
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Farklı model adlarını dene
        model_names = ['gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro', 'gemini-1.5-flash']
        model = None
        
        for model_name in model_names:
            try:
                print(f"🔄 Analiz için {model_name} modelini deniyorum...")
                model = genai.GenerativeModel(model_name)
                # Test çağrısı yap
                test_response = model.generate_content("Hello")
                print(f"✅ Analiz modeli {model_name} başarıyla yüklendi")
                break
            except Exception as e:
                print(f"❌ Analiz modeli {model_name} çalışmadı: {e}")
                continue
        
        if model is None:
            print("❌ Hiçbir model çalışmadı, fallback kullanılıyor")
            return get_fallback_analysis()
        
        # Analiz prompt'u - Çok daha detaylı ve spesifik
        analysis_prompt = f"""
        Analyze this English conversation for a language learning app. Provide extremely detailed, specific, and constructive feedback in Turkish:

        User's conversation:
        {conversation_text}

        Please analyze and provide feedback in the following format:

        VOCABULARY: 
        [Çok detaylı kelime analizi yap:
        1. İyi kullandığı kelimeler: (kelime listesi ve neden iyi olduğu)
        2. Yanlış kullandığı kelimeler: "Yanlış: ... Doğru: ..." formatında
        3. Öğrenebileceği yeni kelimeler: (konuyla ilgili 5-10 yeni kelime)
        4. Kelime çeşitliliği puanı: (1-10 arası)
        5. Kelime seviyesi: (A1/A2/B1/B2)
        6. Özel öneriler: (kelime öğrenme teknikleri)]

        GRAMMAR: 
        [Detaylı gramer analizi:
        1. Tespit edilen hatalar: Her hatayı "Yanlış: ... Doğru: ... Açıklama: ..." formatında
        2. Doğru kullandığı gramer yapıları: (liste halinde)
        3. Öğrenmesi gereken gramer kuralları: (öncelik sırasına göre)
        4. Gramer puanı: (1-10 arası)
        5. En sık yapılan hatalar: (pattern analizi)
        6. Gramer önerileri: (hangi konulara odaklanmalı)]

        PRONUNCIATION: 
        [Telaffuz rehberi:
        1. Telaffuzu zor kelimeler: "Kelime: ... Doğru telaffuz: ... IPA: ..." formatında
        2. Yanlış telaffuz edilen kelimeler: "Yanlış: ... Doğru: ..." formatında
        3. İngilizce ses kuralları: (hangi seslere dikkat etmeli)
        4. Telaffuz puanı: (1-10 arası)
        5. Pratik önerileri: (telaffuz egzersizleri)
        6. Online kaynaklar: (telaffuz için)]

        ALTERNATIVES: 
        [Alternatif ifadeler rehberi:
        1. Kullandığı ifadelerin alternatifleri: "Kullandığın: ... Daha iyi alternatif: ... Neden daha iyi: ..." formatında
        2. Daha doğal ifadeler: (günlük konuşma için)
        3. Daha resmi ifadeler: (iş ortamı için)
        4. İfade çeşitliliği: (aynı anlamı veren farklı yollar)
        5. İfade önerileri: (her durum için)]

        FLUENCY: 
        [Konuşma akıcılığı analizi:
        1. Akıcılık puanı: (1-10 arası)
        2. Konuşma hızı: (çok yavaş/yavaş/normal/hızlı/çok hızlı)
        3. Duraksama analizi: (nerede duraksadı, neden)
        4. Cümle bağlantıları: (nasıl cümleleri bağladı)
        5. Düşünce akışı: (mantıklı mı, karışık mı)
        6. Akıcılık önerileri: (nasıl daha akıcı konuşabilir)
        7. Pratik teknikleri: (akıcılık için egzersizler)]

        COMMUNICATION: 
        [İletişim becerileri analizi:
        1. İletişim puanı: (1-10 arası)
        2. Aktif dinleme: (karşı tarafı anladı mı)
        3. Soru sorma: (uygun sorular sordu mu)
        4. Konuşma başlatma: (nasıl konuşma başlattı)
        5. Konuşma sürdürme: (konuşmayı nasıl sürdürdü)
        6. Konuşma sonlandırma: (nasıl bitirdi)
        7. İletişim önerileri: (daha iyi iletişim için)]

        RECOMMENDATIONS: 
        [Kapsamlı öğrenme önerileri:
        1. Kısa vadeli hedefler: (1-2 hafta içinde yapabilecekleri)
        2. Orta vadeli hedefler: (1-2 ay içinde)
        3. Uzun vadeli hedefler: (3-6 ay içinde)
        4. Günlük pratik önerileri: (her gün yapabilecekleri)
        5. Online kaynaklar: (websiteler, uygulamalar, YouTube kanalları)
        6. Kitap önerileri: (seviyesine uygun kitaplar)
        7. Film/Dizi önerileri: (İngilizce öğrenme için)
        8. Pratik partnerleri: (nasıl bulabilir)
        9. Sınav hazırlığı: (varsa sınav hedefleri)
        10. Motivasyon önerileri: (nasıl motivasyonunu koruyabilir)]

        Her bölüm için çok detaylı, spesifik, yapıcı ve pratik geri bildirim ver. Kullanıcının seviyesini A2 olarak düşün. Her hatayı, öneriyi ve kaynağı açık bir şekilde belirt. Mümkün olduğunca çok örnek ver ve pratik öneriler sun.
        """
        
        print("📤 Gemini'ye analiz isteği gönderiliyor...")
        
        # Gemini API ile analiz
        response = model.generate_content(analysis_prompt)
        analysis_result = response.text
        
        print(f"✅ AI yanıtı alındı: {analysis_result[:100]}...")
        
        # Sonuçları parse et
        sections = {
            'vocabulary': '',
            'grammar': '',
            'pronunciation': '',
            'alternatives': '',
            'fluency': '',
            'communication': '',
            'recommendations': ''
        }
        
        current_section = None
        for line in analysis_result.split('\n'):
            line = line.strip()
            if line.startswith('VOCABULARY:'):
                current_section = 'vocabulary'
                sections['vocabulary'] = line.replace('VOCABULARY:', '').strip()
            elif line.startswith('GRAMMAR:'):
                current_section = 'grammar'
                sections['grammar'] = line.replace('GRAMMAR:', '').strip()
            elif line.startswith('PRONUNCIATION:'):
                current_section = 'pronunciation'
                sections['pronunciation'] = line.replace('PRONUNCIATION:', '').strip()
            elif line.startswith('ALTERNATIVES:'):
                current_section = 'alternatives'
                sections['alternatives'] = line.replace('ALTERNATIVES:', '').strip()
            elif line.startswith('FLUENCY:'):
                current_section = 'fluency'
                sections['fluency'] = line.replace('FLUENCY:', '').strip()
            elif line.startswith('COMMUNICATION:'):
                current_section = 'communication'
                sections['communication'] = line.replace('COMMUNICATION:', '').strip()
            elif line.startswith('RECOMMENDATIONS:'):
                current_section = 'recommendations'
                sections['recommendations'] = line.replace('RECOMMENDATIONS:', '').strip()
            elif current_section and line:
                sections[current_section] += ' ' + line
        
        # Boş bölümler için fallback
        for key in sections:
            if not sections[key].strip():
                sections[key] = get_fallback_analysis()[key]
        
        print("✅ AI analizi başarıyla tamamlandı")
        return sections
        
    except Exception as e:
        print(f"❌ AI analizi hatası: {e}")
        print(f"❌ Hata türü: {type(e).__name__}")
        return get_fallback_analysis()

def get_fallback_analysis():
    """Fallback analiz sonuçları - Çok detaylı"""
    return {
        'vocabulary': '''KELİME ANALİZİ:
        
1. İyi kullandığın kelimeler: Temel günlük kelimeleri (hello, how, are, you, good, thank you) doğru kullanmışsın.

2. Yanlış kullandığın kelimeler: Henüz detaylı analiz yapılamadı, daha fazla mesaj göndermeyi dene.

3. Öğrenebileceğin yeni kelimeler: 
   - Günlük konuşma: "awesome", "fantastic", "wonderful", "amazing", "brilliant"
   - Duygular: "excited", "thrilled", "delighted", "pleased", "satisfied"
   - Aksiyonlar: "explore", "discover", "achieve", "accomplish", "succeed"

4. Kelime çeşitliliği puanı: 6/10 (temel seviye)

5. Kelime seviyesi: A2 (orta başlangıç)

6. Özel öneriler: 
   - Her gün 5 yeni kelime öğren
   - Kelime kartları kullan
   - Yeni kelimeleri cümle içinde kullan
   - Kelime defteri tut''',

        'grammar': '''GRAMER ANALİZİ:
        
1. Tespit edilen hatalar: Henüz detaylı analiz yapılamadı, daha fazla mesaj göndermeyi dene.

2. Doğru kullandığın gramer yapıları: Basit present tense, temel soru yapıları.

3. Öğrenmen gereken gramer kuralları (öncelik sırasına göre):
   - Present Continuous Tense
   - Past Simple Tense
   - Future Tense (will/going to)
   - Modal Verbs (can, could, would, should)
   - Articles (a, an, the)

4. Gramer puanı: 7/10 (temel seviye)

5. En sık yapılan hatalar: Henüz analiz edilemedi.

6. Gramer önerileri:
   - Gramer kitapları oku
   - Online gramer testleri çöz
   - Gramer uygulamaları kullan
   - Düzenli gramer pratiği yap''',

        'pronunciation': '''TELAFFUZ REHBERİ:
        
1. Telaffuzu zor kelimeler:
   - "Pronunciation" → /prəˌnʌnsiˈeɪʃən/
   - "Beautiful" → /ˈbjuːtɪfʊl/
   - "Interesting" → /ˈɪntrəstɪŋ/
   - "Comfortable" → /ˈkʌmftəbəl/
   - "Wednesday" → /ˈwenzdeɪ/

2. Yanlış telaffuz edilen kelimeler: Henüz analiz edilemedi.

3. İngilizce ses kuralları:
   - "th" sesi (think, this)
   - "r" sesi (rolling r değil)
   - "w" ve "v" farkı
   - "sh" ve "ch" sesleri
   - Vurgu kuralları

4. Telaffuz puanı: 6/10

5. Pratik önerileri:
   - Forvo.com kullan
   - YouTube telaffuz videoları izle
   - Ayna karşısında pratik yap
   - Kayıt yap ve dinle

6. Online kaynaklar:
   - BBC Learning English
   - Rachel's English
   - English with Lucy''',

        'alternatives': '''ALTERNATİF İFADELER REHBERİ:
        
1. Kullandığın ifadelerin alternatifleri:
   - "I am" → "I'm" (daha doğal)
   - "I want" → "I'd like" (daha nazik)
   - "Thank you" → "Thanks a lot", "Much appreciated"
   - "Good" → "Great", "Excellent", "Wonderful"
   - "Hello" → "Hi there", "Hey", "Good morning/afternoon"

2. Daha doğal ifadeler:
   - "How are you?" → "How's it going?", "What's up?"
   - "I don't know" → "I'm not sure", "I have no idea"
   - "I like" → "I'm into", "I'm a fan of"
   - "I think" → "I believe", "In my opinion"

3. Daha resmi ifadeler:
   - "I want" → "I would like to"
   - "I need" → "I require"
   - "I think" → "I believe that"
   - "I don't know" → "I'm not certain"

4. İfade çeşitliliği: Aynı anlamı veren farklı yollar kullan.

5. Konuşma akıcılığı: Daha fazla pratik yap.

6. İfade önerileri: Her durum için uygun ifadeler öğren.''',

        'fluency': '''KONUŞMA AKICILIĞI ANALİZİ:
        
1. Akıcılık puanı: 6/10 (orta seviye)

2. Konuşma hızı: Normal (temel seviye için uygun)

3. Duraksama analizi: 
   - Kelime arama sırasında duraksama
   - Gramer düşünürken duraksama
   - Doğal konuşma akışı için daha fazla pratik gerekli

4. Cümle bağlantıları: 
   - Basit bağlaçlar kullanıyor (and, but, because)
   - Daha karmaşık bağlaçlar öğrenmeli

5. Düşünce akışı: Mantıklı ama basit

6. Akıcılık önerileri:
   - Günlük konuşma pratiği yap
   - Kelime hazinesini genişlet
   - Gramer kurallarını otomatikleştir
   - Konuşma hızını artır

7. Pratik teknikleri:
   - Shadowing tekniği (söyleneni tekrarla)
   - Tongue twisters (dil twister'ları)
   - Hızlı konuşma egzersizleri
   - Kayıt yapıp dinleme''',

        'communication': '''İLETİŞİM BECERİLERİ ANALİZİ:
        
1. İletişim puanı: 7/10 (iyi seviye)

2. Aktif dinleme: 
   - Bot'un sorularına cevap veriyor
   - Konuşma konusunu takip ediyor
   - Daha derinlemesine dinleme geliştirilebilir

3. Soru sorma: 
   - Basit sorular sorabiliyor
   - Daha karmaşık sorular öğrenmeli
   - Soru çeşitliliği artırılmalı

4. Konuşma başlatma: 
   - Temel selamlaşma yapabiliyor
   - Konuşma konusu önerebiliyor
   - Daha doğal başlangıçlar öğrenmeli

5. Konuşma sürdürme: 
   - Basit konuları sürdürebiliyor
   - Daha uzun konuşmalar için pratik gerekli
   - Konuşma derinliği artırılmalı

6. Konuşma sonlandırma: 
   - Temel veda ifadeleri kullanıyor
   - Daha doğal sonlandırma öğrenmeli

7. İletişim önerileri:
   - Daha fazla soru sorma pratiği
   - Aktif dinleme teknikleri
   - Konuşma başlatma stratejileri
   - Konuşma sürdürme teknikleri''',

        'recommendations': '''KAPSAMLI ÖĞRENME ÖNERİLERİ:
        
1. Kısa vadeli hedefler (1-2 hafta):
   - Her gün 5 yeni kelime öğren
   - Günlük 15 dakika İngilizce dinleme
   - Basit gramer kurallarını tekrarla
   - Telaffuz pratiği yap
   - Günlük konuşma pratiği (10 dakika)

2. Orta vadeli hedefler (1-2 ay):
   - 200 yeni kelime öğren
   - Bir İngilizce kitap oku
   - Online dil değişim partneri bul
   - Gramer seviyesini geliştir
   - Akıcılık egzersizleri yap

3. Uzun vadeli hedefler (3-6 ay):
   - B1 seviyesine ulaş
   - İngilizce film/dizi izle
   - İngilizce podcast dinle
   - Yazma becerilerini geliştir
   - İletişim becerilerini geliştir

4. Günlük pratik önerileri:
   - 15 dakika İngilizce dinleme
   - 10 dakika okuma
   - 5 yeni kelime öğrenme
   - Basit cümleler yazma
   - 10 dakika konuşma pratiği

5. Online kaynaklar:
   - Duolingo, Memrise, Babbel
   - BBC Learning English
   - YouTube: English with Lucy, Rachel's English
   - Grammarly (yazma için)
   - HelloTalk (konuşma pratiği)

6. Kitap önerileri:
   - "English Grammar in Use" (Raymond Murphy)
   - "Oxford Word Skills" serisi
   - "Cambridge English Vocabulary in Use"
   - "English Conversation" kitapları

7. Film/Dizi önerileri:
   - Friends (başlangıç için)
   - Modern Family
   - The Office
   - Ted Talks (YouTube)
   - İngilizce altyazılı izle

8. Pratik partnerleri:
   - HelloTalk uygulaması
   - Tandem uygulaması
   - iTalki (online dersler)
   - Meetup grupları
   - Discord İngilizce kanalları

9. Sınav hazırlığı:
   - Cambridge English sınavları
   - IELTS hazırlık
   - TOEFL hazırlık
   - Speaking sınavları için pratik

10. Motivasyon önerileri:
   - Günlük hedefler belirle
   - İlerleme takibi yap
   - Ödül sistemi kur
   - İngilizce arkadaşlar edin
   - Başarı günlüğü tut'''
    }

def generate_gemini_mc_questions(topic, api_key=None, num_questions=10, language='en'):
    """
    Gemini API ile çoktan seçmeli sorular üretir.
    :param topic: Konu başlığı (ör. 'selamlaşma')
    :param api_key: Gemini API anahtarı (varsayılan: ortam değişkeni)
    :param num_questions: Kaç soru üretilecek
    :param language: Soru dili (varsayılan: İngilizce)
    :return: [{'tr': ..., 'secenekler': [...], 'dogru': ...}, ...]
    """
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY')
    
    # API anahtarı yoksa hata ver
    if not api_key:
        raise ValueError('Gemini API anahtarı bulunamadı! Lütfen GEMINI_API_KEY ortam değişkenini ayarlayın.')

    # Topic'e göre prompt oluştur
    if 'yemek' in topic.lower() or 'food' in topic.lower():
        # Yemek konusu için özel prompt
        prompt = (
            f"Konu: {topic}\n"
            f"Aşağıda {num_questions} adet YEMEK KONUSUNDA doğal ve günlük konuşma tarzında çoktan seçmeli soru üret. Her soru için:\n"
            "- 'tr': Türkçe, yemek konusunda günlük konuşmada kullanılan doğal soru\n"
            "- 'secenekler': 4 İngilizce seçenek (3 yanlış, 1 doğru)\n"
            "- 'dogru': Doğru İngilizce cevap\n"
            "ÖNEMLİ KURALLAR:\n"
            "- TÜM SORULAR YEMEK/İÇECEK KONUSUNDA OLSUN\n"
            "- Sorular doğal ve günlük konuşma tarzında olsun\n"
            "- 'X İngilizce nasıl söylenir?'\n"
            "- Günlük hayatta yemek konusunda gerçekten sorulan sorular olsun\n"
            "- Seçenekler mantıklı ve gerçekçi olsun\n"
            "- Yanlış seçenekler de yemek/yiyecek/nesne kategorisinde olsun\n"
            "- KARMAŞIK YEMEK SORULARI (pişirme yöntemleri, malzeme seçimi)\n"
            "- TARİFLER VE BÖLGESEL YEMEKLER YOK (Urfa, Adana, İzmir vb. yemekleri)\n"
            "Sadece JSON array döndür. Format:\n"
            "[\n  {'tr': '...', 'secenekler': ['...', '...', '...', '...'], 'dogru': '...'},\n  ...\n]\n"
            f"Soruların dili: {language}. TÜM SORULAR YEMEK/İÇECEK KONUSUNDA OLSUN - KARMAŞIK YEMEK SORULARI YOK."
        )
    else:
        # Genel konular için (selamlaşma vb.) genel prompt
        prompt = (
            f"Konu: {topic}\n"
            f"Aşağıda {num_questions} adet {topic} konusunda doğal ve günlük konuşma tarzında çoktan seçmeli soru üret. Her soru için:\n"
            "- 'tr': Türkçe, {topic} konusunda günlük konuşmada kullanılan doğal soru\n"
            "- 'secenekler': 4 İngilizce seçenek (3 yanlış, 1 doğru)\n"
            "- 'dogru': Doğru İngilizce cevap\n"
            "ÖNEMLİ KURALLAR:\n"
            "- TÜM SORULAR {topic} KONUSUNDA OLSUN\n"
            "- Sorular doğal ve günlük konuşma tarzında olsun\n"
            "- 'X İngilizce nasıl söylenir?'\n"
            "- Günlük hayatta {topic} konusunda gerçekten sorulan sorular olsun\n"
            "- Seçenekler mantıklı ve gerçekçi olsun\n"
            "- Yanlış seçenekler de aynı kategoride olsun\n"
            "- YİYECEK/İÇECEK/YEMEK KONULARI HARİÇ\n"
            "Sadece JSON array döndür. Format:\n"
            "[\n  {'tr': '...', 'secenekler': ['...', '...', '...', '...'], 'dogru': '...'},\n  ...\n]\n"
            f"Soruların dili: {language}. TÜM SORULAR {topic} KONUSUNDA OLSUN - YİYECEK/İÇECEK KONULARI HARİÇ."
        )

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"Gemini API hatası: {response.status_code} {response.text}")
    result = response.json()
    # Yanıttan JSON array'i ayıkla
    try:
        import json as pyjson
        text = result['candidates'][0]['content']['parts'][0]['text']
        # Kod bloğu işaretlerini temizle
        text = re.sub(r"^```json|^```|```$", "", text.strip(), flags=re.MULTILINE).strip()
        questions = pyjson.loads(text)
        return questions
    except Exception as e:
        raise Exception(f"Gemini yanıtı ayrıştırılamadı: {e}\nYanıt: {result}")
