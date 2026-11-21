# Auto Lyrics Sync Pro

यह project Smart Digital Seva repository में अलग folder `/lyrics-sync/` में रखा गया है। मुख्य website का root `index.html` बदला नहीं गया है।

## Features
- Audio upload (40 MB तक)
- पूरा Lyrics एक साथ paste
- Whisper AI speech recognition और अनुमानित line-level timing alignment
- Live lyrics preview
- SRT captions और JSON timing export

## Deployment (दो भाग)

### 1. Frontend: GitHub Pages
इस repository की Settings → Pages में Deploy from branch चुनें, branch `main`, folder `/ (root)` रखें। यदि Pages पहले से चालू है तो नया पेज इस URL पर उपलब्ध होगा:
`https://smartdigitalseva05-hash.github.io/Smartdigital-seva/lyrics-sync/`

### 2. AI backend: Render
GitHub पर इस repository को Render से connect करें और Root Directory `lyrics-sync` रखें।
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment variable: `WHISPER_MODEL=small`

Deploy होने के बाद Render का URL वेबसाइट के **AI Server URL** बॉक्स में डालें। मॉडल पहली बार डाउनलोड होने में समय और disk/RAM लग सकती है। Render free instance पर लंबे audio/model requests की सीमाएँ हो सकती हैं; production के लिए पर्याप्त RAM/CPU वाला server लें।

## Important accuracy note
Whisper singing/भजन के शब्दों को हमेशा सही नहीं पहचानता। इस MVP में transcript के शब्दों से pasted lyric lines का approximate alignment होता है; गलत पहचाने या दोहराए गए शब्दों के कारण कुछ lines unmatched/गलत समय पर हो सकती हैं। Review और correction workflow आगे जोड़ना चाहिए। यह अभी word-by-word karaoke highlighting या MP4 video export नहीं है।

## Security / privacy
- Audio configured backend पर upload होता है; backend temporary file को processing के बाद delete करता है।
- Public launch से पहले authentication, rate limiting, request queue, stronger upload controls, restricted CORS origins और privacy notice जोड़ें।
- निजी/कॉपीराइट audio तभी upload करें जब आपके पास उपयोग का अधिकार हो।
