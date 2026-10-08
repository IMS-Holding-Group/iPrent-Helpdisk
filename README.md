# iPrent Helpdisk

نظام ويب لتذاكر الدعم الفني، مع طابعات وأجهزة وتنبيهات وجدولة صيانة وتوقع حبر وتصنيف نصي وأدوار ثلاثة: مدير ودعم وموظف.

## 1 ما هو المشروع

`app.py` تطبيق Flask-SQLAlchemy على SQLite في `database.db`. الواجهة العربية عبر قوالب لوحة للطاقم وبوابة للموظف. الملف يراقب الطابعات بخيط SNMP إذا توفرت مكتبة `pysnmp`، ويولد تذاكر تلقائية، ويقترح أولوية واستجابة.

الاسم في README السابق: iPrent Helpdisk. الشعار والمسار `/assets` يخدمان مجلد `assets`.

## 2 لماذا وُجد المشروع

README السابق الصحيح في وصفه العام: جمع أعطال الطابعات والشبكة والأجهزة والبرمجيات في تذاكر، مع لوحة حالة ومتابعة. الكود يضيف بذرة طابعات وعناوين `192.168.1.100` حتى `192.168.1.109` وتذاكر تجريبية عند أول تشغيل عبر `init_db`.

## 3 المستخدمون

الأدوار في الكود: `admin` و `support` و `employee`. طاقم الدعم هو `admin` و `support`.

حسابات تُزرع في `seed_default_users` إن غاب اسم المستخدم:

| المستخدم | كلمة المرور في المصدر | الدور | البريد المخزن |
| --- | --- | --- | --- |
| admin |  | admin | admin@helpdesk.local |
| support | support123 | support | support@helpdesk.local |
| employee | employee123 | employee | employee@company.local |

البصمة عبر `generate_password_hash`.

## 4 المميزات

- تذاكر بحالات وأولويات وتعليقات وربط بطابعة أو جهاز.
- بوابة موظف على `/portal` وعرض تذكرته على `/portal/ticket/<id>`.
- لوحة طاقم على `/dashboard`.
- قائمة طابعات وأجهزة.
- تنبيهات وقراءتها.
- توقع نفاد الحبر في `predict_ink_depletion`.
- جدول صيانة إنشاء وعرض.
- أنماط أعطال الطابعة إذا وُجدت ثلاث تذاكر على الأقل في `detect_patterns`.
- أولوية آلية في `calculate_ai_priority`.
- تصنيف نصي في `categorize_ticket_nlp`.
- رد آلي في `generate_ai_response`.
- تدريب من `POST /ai/train` وسكربت `train_model.py` ونموذج `ai_model.py`.
- مراقبة SNMP كل 300 ثانية داخل `snmp_monitoring_worker` عند توفر المكتبة.

## 5 سير العمل

```
دخول
  |
  +-- employee --> /portal --> تذكرة خاصة به
  |
  +-- admin أو support --> /dashboard --> تذاكر وأجهزة وتنبيهات
                |
                +-- خيط SNMP إن توفر --> تذكرة تلقائية أو تنبيه
                |
                +-- تعليق وتغيير حالة ورد آلي
```

## 6 أمثلة خطوات حقيقية

1. `pip install -r requirements.txt`.
2. `python app.py`. يحاول `migrate_database` ثم `init_db` ثم خيط SNMP ثم الاستماع على `127.0.0.1:5000` مع `debug=True`.
3. الدخول بـ `employee` يفتح البوابة. الدخول بـ `admin` أو `support` يفتح اللوحة.
4. الموظف ينشئ تذكرة من البوابة. الطاقم يراها في `/tickets` ويضيف تعليقاً ويغير الحالة.
5. `POST /printers/<id>/monitor` يشغل فحص طابعة واحدة.
6. إن كان `SNMP_AVAILABLE` يدور العامل كل 5 دقائق، وعند الخطأ ينتظر 60 ثانية.

## 7 رحلة المستخدم

الموظف: دخول، بوابة، إنشاء تذكرة، متابعة تذاكره فقط لأن `user_can_access_ticket` يسمح للموظف بتذكرته ذات `created_by_user_id`.

الدعم: لوحة، كل التذاكر، تعليقات، حالات، تنبيهات، صيانة، أنماط.

المدير: ما يصل إليه الدعم، إضافة إلى ما يغلّفه `admin_required` مثل ما يظهر من مسار التدريب إن كان محمياً بهذا الغلاف.

`/` يحوّل حسب الدور عبر `home_redirect`.

## 8 الوحدات

| الملف | الدور |
| --- | --- |
| `app.py` | النماذج والمسارات والمراقبة |
| `config.py` | مسار القاعدة ومفتاح الجلسة |
| `ai_model.py` | صنف `AITicketModel` |
| `train_model.py` | `prepare_training_data` و `train_ai_model` بعدد دورات افتراضي 50 |
| `migrate_db.py` | ترحيل عند الإقلاع |
| `models/model_info.json` | معلومات تدريب |
| `templates/` | `layout` و `login` و `index` و `dashboard` و `ticket_view` و `portal_layout` و `employee_portal` و `employee_ticket` |
| `static/js/main.js` و `employee.js` | سلوك الواجهة |
| `assets` | خطوط وأصول |

تعارض مع README السابق: يذكر `models/ticket_ai_model.h5` و `tokenizer.pkl` و `encoders.pkl`. المجلد الحالي فيه `model_info.json` فقط.

## 9 الكيانات

نماذج SQLAlchemy: `Printer`، `Ticket`، `TicketComment`، `User`، `Alert`، `MaintenanceSchedule`، `InkPrediction`، `TicketCategory`، `AIResponse`، `Device`.

`model_info.json` يحفظ: `vocab_size` 5000، `max_length` 200، `embedding_dim` 128، `trained_at` القيمة `2025-12-31T22:00:45.657615`، `is_trained` بالقيمة true.

تعارض: `is_trained` يساوي true بينما ملفات الأوزان غير موجودة في `models/`.

## 10 الصلاحيات

| الإجراء | من يمر |
| --- | --- |
| صفحات الطاقم عبر `staff_required` | admin و support. الموظف يُعاد إلى البوابة |
| `admin_required` | admin، وغير ذلك JSON بحالة 403 والنص Admin access required |
| تذكرة | الطاقم، أو الموظف صاحب `created_by_user_id` |
| بلا جلسة | تحويل إلى `/login` |

`get_user_role`: الدور الغائب أو غير المعروف يصبح `employee`، إلا اسم `admin` فيصبح `admin`.

## 11 الأتمتة

- خيط SNMP دوري.
- `create_auto_ticket` ينشئ تذكرة وتنبيهاً من نوع `auto_generated`.
- تصنيف وأولوية ورد عند إنشاء التذاكر في دوال `generate_ai_response` و `calculate_ai_priority` و `categorize_ticket_nlp`.
- تدريب خلفي بخيط `daemon` من مسار التدريب.

## 12 تكامل الوحدات

الواجهة تنادي مسارات Flask. SNMP ينادي الطابعة ثم قد يكتب تذكرة. نموذج الذكاء يقرأ `models/` إن وُجدت الملفات التي يتوقعها `ai_model.py`. البريد المخزن على المستخدم لا يظهر معه مرسل بريد في الملفات المفحوصة.

## 13 المصطلحات

| المصطلح | المعنى |
| --- | --- |
| Helpdisk | الاسم المكتوب في مجلد المشروع وREADME السابق |
| staff | admin و support |
| ink level | حقل مستوى حبر على الطابعة |
| pattern | تكرار تصنيفات تذاكر الطابعة |

## 14 الأسئلة الشائعة

| السؤال | الجواب |
| --- | --- |
| هل CSRF مفعّل؟ | `Flask-WTF` في المتطلبات. البحث في `app.py` لا يجد `CSRF` أو `csrf` أو `WTF` |
| هل يعمل الذكاء بلا ملفات النموذج؟ | `model_info.json` يقول إن النموذج مدرَّب، والمجلد بلا ملف أوزان. سلوك التحميل يتبع `ai_model.py` عند غياب الملف |
| هل SNMP إلزامي؟ | إن غابت المكتبة يطبع البرنامج أن المراقبة معطلة |
| هل كلمة المرور تُغيَّر من واجهة موثقة هنا؟ | مسار تغيير كلمة المرور غير ظاهر في قائمة المسارات المقروءة |

## 15 البنية

```
المتصفح
   |
   v
Flask 127.0.0.1:5000
   |
   +-- SQLAlchemy --> database.db
   |
   +-- خيط SNMP --> عناوين الطابعات
   |
   +-- ai_model / train_model --> models/
```

## 16 التقنيات

من `requirements.txt`:

| الحزمة | الإصدار |
| --- | --- |
| Flask | 2.2.5 |
| Flask-SQLAlchemy | 2.5.1 |
| SQLAlchemy | 1.4.49 |
| Flask-WTF | 1.0.1 |
| WTForms | 3.0.1 |
| python-dotenv | 0.21.0 |
| Pillow | 9.5.0 |
| pysnmp | 4.4.12 |
| tensorflow | 2.13.0 |
| scikit-learn | 1.3.0 |
| numpy | 1.24.3 |
| pandas | 2.0.3 |
| nltk | 3.8.1 |

Python المطلوب في README السابق: 3.8 أو أحدث. لا قفل إصدار داخل المشروع.

تعارض: `python-dotenv` في المتطلبات. `config.py` لا يستدعي `load_dotenv` ولا يقرأ بيئة للمفتاح.

## 17 شجرة الملفات

```
iPrent Helpdisk/
├── assets/
├── models/
│   └── model_info.json
├── static/
│   └── js/
├── templates/
├── ai_model.py
├── app.py
├── config.py
├── database.db
├── migrate_db.py
├── README.md
├── requirements.txt
└── train_model.py
```

## 18 الواجهة

قوالب لوحة الموظف منفصلة عن قوالب الطاقم. الخطوط العربية مذكورة في README السابق كـ IBM Plex Sans Arabic تحت `assets/fonts`. الصفحة لغة عربية حسب README السابق.

## 19 الخادم

`app.run(debug=True, host='127.0.0.1', port=5000)` في نهاية `app.py`. التشغيل عبر `flask run` مذكور في README السابق ويعتمد إعداد Flask الافتراضي.

`SECRET_KEY` نص ثابت في `config.py`. القيمة غير منقولة هنا. التعليق في الملف يقول للاستخدام المحلي.

## 20 تدفق الطلب

إنشاء تذكرة من `POST /tickets` يمر على التحقق من الجلسة ثم يحفظ التذكرة وقد يحسب تصنيفاً وأولوية ورداً. عرض تذكرة الطاقم على `/ticket/<id>` وعرض الموظف على `/portal/ticket/<id>` مع فحص الملكية.

تعليق: `POST /ticket/<id>/comment`. حالة: `POST /ticket/<id>/status`.

## 21 قاعدة البيانات

SQLite ملف `database.db` من `config.py`. `db.create_all` عند `init_db`. `migrate_db.py` يُستدعى قبل ذلك عند `python app.py`.

## 22 نقاط النهاية

| الطريقة | المسار |
| --- | --- |
| GET | `/` |
| GET, POST | `/login` |
| GET | `/logout` |
| GET | `/dashboard` |
| GET | `/portal` |
| GET | `/portal/ticket/<ticket_id>` |
| GET | `/printers` |
| GET | `/devices` |
| GET, POST | `/tickets` |
| GET | `/ticket/<ticket_id>` |
| POST | `/ticket/<ticket_id>/comment` |
| POST | `/ticket/<ticket_id>/status` |
| GET | `/ticket-types` |
| POST | `/ai/train` |
| GET | `/ai/status` |
| GET | `/alerts` |
| POST | `/alerts/<alert_id>/read` |
| GET | `/predictions/ink` |
| GET, POST | `/maintenance/schedule` |
| GET | `/analytics/patterns/<printer_id>` |
| POST | `/analytics/ai-priority` |
| GET | `/ticket/<ticket_id>/ai-response` |
| POST | `/printers/<printer_id>/monitor` |
| GET | `/assets/<filename>` |

حماية كل مسار تتبع المزخرف المكتوب فوقه في `app.py`: عام، أو `login_required`، أو `staff_required`، أو `admin_required`.

## 23 المصادقة

جلسة Flask بعد مطابقة البصمة. الحقول المخزنة في الجلسة تشمل معرف المستخدم والدور بما يكفي لـ `home_redirect` وبوابات الصلاحية.

لا حد لمحاولات الدخول ظاهر في دوال الدخول المقروءة. لا CSRF في `app.py`.

## 24 الأمان الموجود في الكود

| البند | الواقع |
| --- | --- |
| كلمات المرور | بصمة Werkzeug، ونصوص البذرة ظاهرة في `seed_default_users` |
| مفتاح الجلسة | ثابت في `config.py` |
| التصحيح | `debug=True` |
| فصل الموظف | تحويل من صفحات الطاقم وفحص مالك التذكرة |
| SNMP community | الدالة `get_printer_snmp_data` تأخذ `community='public'` كقيمة افتراضية |
| dotenv | الحزمة مثبتة في المتطلبات وغير مستخدمة في `config.py` |
| Flask-WTF | في المتطلبات وغير مستدعى في `app.py` |

## 25 الإعدادات

`BASE_DIR` و `DATABASE_PATH` و `SQLALCHEMY_DATABASE_URI` و `SQLALCHEMY_TRACK_MODIFICATIONS = False` و `SECRET_KEY` داخل `config.py`.

لا أسماء متغيرات بيئة مقروءة من هذا الملف.

## 26 التكاملات

- SNMP نحو عناوين الطابعات المزروعة على الشبكة `192.168.1.0/24` كنصوص IP.
- TensorFlow و scikit-learn و NLTK حسب المتطلبات وملفات النموذج.
- لا بوابة بريد في الملفات المفحوصة رغم وجود عمود بريد.

## 27 المهام المجدولة

خيط دائم وليس جدولة نظام التشغيل: نوم 300 ثانية بين جولات SNMP، و60 ثانية بعد خطأ الجولة.

## 28 الملفات

| المسار | المحتوى |
| --- | --- |
| `database.db` | بيانات التشغيل |
| `models/model_info.json` | وصف التدريب |
| `assets` | خطوط وملفات ثابتة تُخدم من `/assets` |

## 29 السجلات

`print` عند الترحيل وبدء SNMP وأخطاء المراقبة. لا ملف سجل مخصص ظاهر.

## 30 التثبيت

```
pip install -r requirements.txt
python app.py
```

README السابق يذكر `python train_model.py` اختيارياً بعد وجود تذاكر. التدريب قد يستغرق دقائق حسب ذلك الشرح.

العنوان: `http://127.0.0.1:5000/`.

## 31 دليل التطوير

- الأدوار في الثابت `ROLES`.
- البذرة في `init_db` و `seed_default_users`.
- أي مسار جديد للطاقم يحتاج المزخرف المناسب وإلا يصبح متاحاً حسب ما يكتبه المطور.
- لا ترفع رقم الإصدار تلقائياً. `model_info.json` ليس ملف إصدار تطبيق.

## 32 النشر

غير موثق. لا `Procfile`. التشغيل المكتوب تطوير محلي على `127.0.0.1` مع التصحيح.

## 33 النسخ الاحتياطي

غير موثق. الملف الحامل للبيانات هو `database.db`.

## 34 استكشاف الأخطاء

| العرض | الاتجاه من الكود |
| --- | --- |
| SNMP monitoring disabled | المكتبة غير متاحة في البيئة |
| Warning عند الترحيل | استثناء داخل `migrate_database` يُطبع ولا يوقف الإقلاع |
| 403 Admin access required | المسار تحت `admin_required` والدور ليس admin |
| الموظف لا يرى لوحة الطاقم | `staff_required` يعيده إلى البوابة |
| التصنيف الآلي بلا أوزان | مجلد `models` بلا ملفات h5 أو pkl حالياً |

## 35 التبعيات

القائمة الكاملة في القسم 16، مثبّتة بأرقام في `requirements.txt`.

## 36 القيود

- حسابات بذرة معروفة في المصدر.
- مفتاح جلسة ثابت.
- تصحيح مفعّل.
- مجتمع SNMP الافتراضي `public`.
- حزمة CSRF غير موصولة في `app.py`.
- ملف معلومات النموذج يقول إنه مدرَّب والملفات الثنائية غير موجودة.
- عناوين الطابعات تجريبية على شبكة محلية افتراضية.

## 37 الحالة الحالية

التطبيق قابل للتشغيل المحلي مع قاعدة موجودة `database.db`. README السابق صحيح في الأدوار والميزات العامة والمسارات الرئيسة، ويذكر ملفات نموذج غير موجودة الآن، ويذكر حماية CSRF عبر Flask-WTF بينما `app.py` لا يستدعيها.

## 38 القرارات

| القرار | الأثر |
| --- | --- |
| SQLite | ملف واحد بلا خادم قاعدة |
| ثلاثة أدوار | فصل بوابة الموظف عن لوحة الطاقم |
| SNMP في خيط | المراقبة لا توقف خادم الويب، وتتوقف كلياً إذا غابت المكتبة |
| بذرة طابعات | اللوحة تعرض أجهزة فور أول تشغيل |

## 39 سجل التغييرات

غير موجود في الملفات الحالية. `model_info.json` يحمل وقت تدريب `2025-12-31T22:00:45.657615` وليس سجل إصدارات للمنتج.

## System Overview

مكتب مساعدة للتذاكر والأجهزة. الموظف يتابع طلبه، والدعم يدير الطابور، والمراقبة تحاول قراءة الطابعات عبر SNMP، وطبقة الذكاء تقترح تصنيفاً وأولوية عندما تتوفر بياناتها.

## Quick Reference

| البند | القيمة |
| --- | --- |
| التشغيل | `python app.py` |
| العنوان | `http://127.0.0.1:5000/` |
| المدير | admin /  |
| الدعم | support / support123 |
| الموظف | employee / employee123 |
| القاعدة | `database.db` |
| دورة SNMP | 300 ثانية |

## Quick Start

ثبّت المتطلبات، شغّل `app.py`، ادخل بأحد الحسابات الثلاثة المزروعة. حساب الموظف يفتح البوابة. الحسابان الآخران يفتحان لوحة الطاقم.

## For Non-Technical Users

سجّل الدخول وأنشئ تذكرة تصف العطل. فريق الدعم يراها في اللوحة ويضيف تعليقاً ويغلقها عند الحل. إن كانت الطابعة معرفة في النظام فقد يظهر تنبيه عن الحبر أو الانقطاع عندما تعمل مراقبة SNMP على شبكتك.

## For Developers

ابدأ من مزخرفات `login_required` و `staff_required` و `admin_required`. اربط الأسرار ببيئة تشغيل قبل أي نشر، لأن المفتاح والحسابات في المصدر. لا تفترض وجود ملف الأوزان: تحقق من مجلد `models` قبل تفعيل التدريب أو التصنيف.
