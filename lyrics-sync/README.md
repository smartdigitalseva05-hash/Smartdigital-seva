# Auto Lyrics Sync Pro

यह project Smart Digital Seva repository में अलग folder `/lyrics-sync/` में रखा गया है। मुख्य website का root `index.html` सुरक्षित है और बदला नहीं गया है।

## Features
- Audio upload (Groq mode में 25 MB तक; Sarvam/local mode में 40 MB तक; खाली/zero-byte audio अस्वीकार)
- पूरा Lyrics एक साथ paste (अधिकतम 30,000 characters और 500 non-empty lines)
- Sarvam Saaras v4 Batch API (लंबे audio, phrase timestamps), Groq Whisper (word timestamps) या local Whisper fallback; अनुमानित line-level timing alignment
- Live lyrics preview
- SRT captions और JSON timing export
- 16:9 YouTube तथा 9:16 Shorts के लिए browser-based MP4/WebM lyrics video export

## Local quality checks

Backend helper tests और frontend contract tests third-party AI packages के बिना चलाए जा सकते हैं:

```bash
python -m unittest discover -s lyrics-sync/tests -v
python -m py_compile lyrics-sync/app.py lyrics-sync/lyrics_core.py lyrics-sync/request_limits.py
```

Frontend contract tests duplicate HTML IDs, missing controls, broken label targets, audio picker support, sync/export controls और backend CORS allowlist wiring जाँचते हैं। Backend unit tests lyrics character/line limits, zero-byte और oversized audio, key-aware provider selection, CORS origin parsing, active-job counting और declared-length/chunked request-body limits जाँचते हैं। GitHub Actions push और pull request पर Python syntax, सभी unit/contract tests, HTML structure तथा JavaScript syntax जाँचता है।

## Deployment

### 1. Frontend: GitHub Pages
Repository में `.github/workflows/pages.yml` जोड़ा गया है। GitHub पर **Settings → Pages → Build and deployment → Source → GitHub Actions** चुनें। इसके बाद `main` branch पर push होने पर site deploy होगी।

Frontend URL:
`https://smartdigitalseva05-hash.github.io/Smartdigital-seva/lyrics-sync/`

यदि workflow deploy नहीं होता, GitHub के **Actions** tab में Pages workflow का error देखें।

### 2. AI backend: Render
**एक-क्लिक Blueprint लिंक:** [Render पर Smart Lyrics Sync Backend Deploy करें](https://render.com/deploy?repo=https://github.com/smartdigitalseva05-hash/Smartdigital-seva)

लिंक खोलकर Render में sign in/connect करें और Blueprint deploy की पुष्टि करें। Repository root में `render.yaml` blueprint है; Render API service create करेगा।

- Runtime: Python
- Root Directory: `lyrics-sync`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Optional fallback: `WHISPER_MODEL=tiny`
- Recommended Odia mode: Render → **Environment** में `SARVAM_API_KEY` secret जोड़ें। यह key होने पर backend अपने-आप Sarvam Saaras v4 Batch API चुनेगा। API key केवल backend environment में रखें; उसे HTML, GitHub या browser storage में कभी न डालें।
- Sarvam Batch API में Odia के लिए `od-IN` और `saaras:v4` उपयोग होता है। 2 घंटे तक audio स्वीकार्य है; API phrase/chunk-level timestamps देती है, word-level timestamps नहीं। Lyrics line timing phrase timestamps से अनुमानित रूप से align होती है।
- Groq `GROQ_API_KEY` को fallback के रूप में रखें; Sarvam सफलतापूर्वक चलने के बाद ही इसे हटाएँ।
- Groq fallback mode अपने-आप `whisper-large-v3` चुनता है और word timestamps माँगता है। Groq mode में अधिकतम audio size 25 MB; Sarvam/local mode में backend सीमा 40 MB है। API rate limits / provider availability लागू हो सकती है।
- Groq API key बनाने के लिए [Groq Console API Keys](https://console.groq.com/keys) खोलें। Key बनाने के बाद Render service के Environment में secret value डालें और service redeploy/restart करें। कोई key ChatGPT को न भेजें।
- Website में **AI Server जाँचें** दबाने पर diagnostics बताएगा कि hosted key configured है या अभी local fallback चल रहा है।

Deploy होने के बाद Render का `onrender.com` URL वेबसाइट के **AI Server URL** बॉक्स में डालें। Groq key configure होने पर Render को Whisper model RAM में load नहीं करना पड़ेगा। बिना key के local fallback चलेगा, जो Free instance पर crash हो सकता है।

## Accuracy limitations
Whisper singing/भजन के शब्द हमेशा सही नहीं पहचानता। इस MVP में transcript के शब्दों से pasted lyric lines का approximate alignment होता है; गलत पहचाने या दोहराए गए शब्दों के कारण कुछ lines unmatched/गलत समय पर हो सकती हैं। प्रत्येक लाइन का confidence दिया जाता है। यदि AI को एक भी lyric line का भरोसेमंद match नहीं मिलता, तो AI mode अब पूरे गाने पर काल्पनिक timing नहीं बाँटता—सभी unmatched lines बिना समय के रहेंगी। जरूरत हो तो स्पष्ट रूप से **No-AI mode** चुनकर manual estimated timeline बनाएँ। Preview में हर लाइन का text और Start/End समय manually सुधार सकते हैं; unmatched lines में समय भरकर SRT export किया जा सकता है। यह अभी word-by-word karaoke highlighting नहीं है। Video export browser की MediaRecorder और codec support पर निर्भर है; MP4 उपलब्ध न होने पर WebM चुना जा सकता है।

## Security / privacy
- Audio configured backend पर upload होता है; backend सामान्य job completion/failure पर temporary file delete करता है।
- Upload 40 MB तक सीमित है (Groq mode में 25 MB); zero-byte audio स्वीकार नहीं होता। Lyrics 30,000 characters और अधिकतम 500 non-empty lines तक सीमित हैं। एक ASGI request-body guard multipart parser से पहले oversized `Content-Length` अस्वीकार करता है और chunked requests के वास्तविक bytes भी गिनता है; कुल सीमा में UTF-8 lyrics और multipart overhead शामिल हैं।
- Backend एक समय में प्रति instance अधिकतम एक active sync job स्वीकार करता है; व्यस्त होने पर HTTP 429 देता है। व्यस्तता की शुरुआती जाँच processing की दूसरी temporary copy बनाने से पहले होती है और upload के बाद lock के भीतर दोबारा जाँच होती है, ताकि simultaneous requests की race न हो। यह capacity guard है, per-user/IP rate limiting नहीं।
- Browser CORS allowlist default रूप से केवल production GitHub Pages origin `https://smartdigitalseva05-hash.github.io` स्वीकार करती है। Custom domain के लिए Render Environment में `CORS_ALLOWED_ORIGINS` को comma-separated exact origins (केवल scheme + host + optional port; कोई path नहीं) के रूप में सेट करें। Local development के लिए उदाहरण: `http://localhost:8000,http://127.0.0.1:8000`। Invalid entries और `*` wildcard अस्वीकार होते हैं। CORS authentication नहीं है और direct non-browser API calls को नहीं रोकता।
- Login/authentication अभी लागू नहीं है। Job status process memory में रहता है और Render restart/redeploy होने पर खो सकता है।
- Public launch से पहले authentication, per-user/IP rate limiting, durable job queue, abuse controls और privacy notice जोड़ें।
- निजी/कॉपीराइट audio तभी upload करें जब आपके पास उपयोग का अधिकार हो।
