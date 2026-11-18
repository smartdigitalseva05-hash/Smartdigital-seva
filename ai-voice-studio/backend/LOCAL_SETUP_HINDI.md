# Local AI Voice Studio — आसान सेटअप

यह तरीका Hugging Face ZeroGPU के रोज़ाना 5 मिनट वाले quota पर निर्भर नहीं करता। Mithi v2 Flash आपके अपने कंप्यूटर के CPU पर चलता है। पहली बार Python packages और model डाउनलोड करने के लिए इंटरनेट चाहिए; उसके बाद model files कंप्यूटर की disk से लोड होती हैं।

## ज़रूरी बातें

- Python 3.10 या नया
- 8 GB RAM न्यूनतम सलाह; 16 GB बेहतर
- लगभग 5–8 GB खाली disk space सलाह के तौर पर रखें; वास्तविक उपयोग अलग हो सकता है
- पहली बार तेज़ इंटरनेट
- CPU पर generation धीमा हो सकता है। Daily GPU-minute quota नहीं होगा, लेकिन कंप्यूटर की गति, RAM, बिजली और uptime की सीमाएँ रहेंगी।
- कंप्यूटर चालू और server चल रहा होना चाहिए। GitHub Pages अपने-आप Python model नहीं चला सकता।

## Windows

1. Python 3.10+ इंस्टॉल करें: https://www.python.org/downloads/ और installer में Add Python to PATH चुनें।
2. GitHub repository से ai-voice-studio/backend folder अपने कंप्यूटर पर डाउनलोड करें।
3. इस folder में setup_and_run_windows.bat पर double-click करें।
4. पहली बार dependencies और Mithi model डाउनलोड होंगे; समय लग सकता है।
5. Terminal window खुली रखें। Server चालू रहने पर address http://127.0.0.1:8000 होगा।
6. स्क्रीन पर दिखा private token वेबसाइट के Voice controls → Neural AI → Private API token में डालें। Backend URL में http://127.0.0.1:8000 डालें और Save & test connection दबाएँ।

## Mac / Linux

1. Python 3.10+ और venv उपलब्ध रखें।
2. ai-voice-studio/backend folder डाउनलोड करें।
3. Terminal में उस folder में जाकर चलाएँ:
   chmod +x setup_and_run_linux_mac.sh
   ./setup_and_run_linux_mac.sh
4. स्क्रीन पर दिखे URL और private token को वेबसाइट के Neural AI settings में डालें।

## रोज़ाना उपयोग

- Setup के बाद उसी script को दोबारा चलाएँ; model और dependencies मौजूद हों तो दोबारा download नहीं होंगे।
- Server बंद करने के लिए terminal में Ctrl+C दबाएँ।
- वेबसाइट इस्तेमाल करते समय computer और server चालू रखें।
- Token .voice_api_key में रखा जाता है; इसे किसी को न भेजें और GitHub पर upload न करें। यह file backend .gitignore में ignored है।

## सुरक्षा और सीमाएँ

- Server केवल 127.0.0.1 पर bind होता है; इसे public internet पर expose न करें।
- Browser से localhost connection की अनुमति Chrome पूछ सकता है; केवल अपनी वेबसाइट और अपने local server के लिए अनुमति दें।
- यह local personal-use setup है। दूसरों के लिए public online service बनाने पर HTTPS hosting, authentication, rate limits और compute cost की अलग व्यवस्था चाहिए।
- Mithi v2 Flash Apache-2.0 model है; Hindi, Odia, English सहित 11 भाषाएँ और 10 voices देता है। आवाज़ और Odia pronunciation को प्रकाशित करने से पहले सुनकर जाँचें।
