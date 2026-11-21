# Auto Lyrics Sync Pro

यह project Smart Digital Seva repository में अलग folder `/lyrics-sync/` में रखा गया है। मुख्य website का root `index.html` सुरक्षित है और बदला नहीं गया है।

## Features
- Audio upload (40 MB तक)
- पूरा Lyrics एक साथ paste
- Whisper AI speech recognition और अनुमानित line-level timing alignment
- Live lyrics preview
- SRT captions और JSON timing export

## Deployment

### 1. Frontend: GitHub Pages
Repository में `.github/workflows/pages.yml` जोड़ा गया है। GitHub पर **Settings → Pages → Build and deployment → Source → GitHub Actions** चुनें। इसके बाद `main` branch पर push होने पर site deploy होगी।

Frontend URL:
`https://smartdigitalseva05-hash.github.io/Smartdigital-seva/lyrics-sync/`

यदि workflow deploy नहीं होता, GitHub के **Actions** tab में Pages workflow का error देखें।

### 2. AI backend: Render
Render Dashboard → **New → Blueprint** से इस GitHub repository को connect करें। Repository root में `render.yaml` blueprint है; Render API service create करेगा।

- Runtime: Python
- Root Directory: `lyrics-sync`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment variable: `WHISPER_MODEL=tiny` (कम RAM में चलने के लिए हल्का मॉडल)

Deploy होने के बाद Render का `onrender.com` URL वेबसाइट के **AI Server URL** बॉक्स में डालें। पहली बार मॉडल डाउनलोड होने में समय लगेगा। Free hosting में cold start, RAM, CPU और request-duration की सीमाएँ हो सकती हैं। बेहतर पहचान/लंबे गानों के लिए पर्याप्त RAM वाला paid server और `WHISPER_MODEL=small` विचार करें।

## Accuracy limitations
Whisper singing/भजन के शब्द हमेशा सही नहीं पहचानता। इस MVP में transcript के शब्दों से pasted lyric lines का approximate alignment होता है; गलत पहचाने या दोहराए गए शब्दों के कारण कुछ lines unmatched/गलत समय पर हो सकती हैं। प्रत्येक लाइन का confidence दिया जाता है। Review/edit workflow आगे जोड़ना चाहिए। यह अभी word-by-word karaoke highlighting या MP4 video export नहीं है।

## Security / privacy
- Audio configured backend पर upload होता है; backend temporary file को processing के बाद delete करता है।
- Upload 40 MB तक और lyrics 30,000 characters तक सीमित हैं; server-side authentication और rate limiting अभी नहीं हैं।
- Public launch से पहले authentication, rate limiting, request queue, abuse controls और privacy notice जोड़ें।
- निजी/कॉपीराइट audio तभी upload करें जब आपके पास उपयोग का अधिकार हो।
