# Google Form setup — step by step

Enquiries are saved in PostgreSQL **and** pushed into a Google Form so your team
gets a live Google Sheet. To do that, Django needs the form ID plus the
`entry.XXXXXXXX` id of every question.

## 1. Create the form

Go to https://forms.google.com → **Blank form**. Name it e.g. `Website Enquiries`.

## 2. Add these questions (all "Short answer", except Message = "Paragraph")

| # | Question title | Type          | Maps to env var                 |
|---|----------------|---------------|---------------------------------|
| 1 | Name           | Short answer  | `GOOGLE_FORM_ENTRY_NAME`        |
| 2 | Email          | Short answer  | `GOOGLE_FORM_ENTRY_EMAIL`       |
| 3 | Phone          | Short answer  | `GOOGLE_FORM_ENTRY_PHONE`       |
| 4 | Subject        | Short answer  | `GOOGLE_FORM_ENTRY_SUBJECT`     |
| 5 | Message        | Paragraph     | `GOOGLE_FORM_ENTRY_MESSAGE`     |
| 6 | Service / Type | Short answer  | `GOOGLE_FORM_ENTRY_TYPE`        |
| 7 | Item title     | Short answer  | `GOOGLE_FORM_ENTRY_ITEM_TITLE`  |
| 8 | Item type      | Short answer  | `GOOGLE_FORM_ENTRY_ITEM_TYPE`   |

Important: leave every question **not required** and do NOT enable
"Limit to 1 response" or "Collect email addresses" — those block server-side posts.

## 3. Get the form ID

Click **Send → link icon (🔗)** and copy the URL. It looks like:

```text
https://docs.google.com/forms/d/e/1FAIpQLSdXXXXXXXXXXXXXXXXXXXXXX/viewform
                                  ^--------- this is GOOGLE_FORM_ID ---------^
```

You may paste either the bare ID or the whole `/viewform` URL into `GOOGLE_FORM_ID`.

## 4. Get each `entry.` id

1. Open the live form (the `/viewform` link) in Chrome.
2. Right click → **View page source** (`Ctrl+U`).
3. Press `Ctrl+F` and search for the question title, e.g. `Phone`.
4. Just before/after it you will see something like `"entry.1234567890"`.
5. Copy that number for each question.

Faster alternative: click the **⋮ menu → Get pre-filled link**, type dummy answers
into every field, press **Get link → Copy link**. The copied URL contains all ids:

```text
...viewform?usp=pp_url&entry.1111111111=John&entry.2222222222=john@mail.com&...
```

## 5. Fill `.env`

```env
GOOGLE_FORM_ID=1FAIpQLSdXXXXXXXXXXXXXXXXXXXXXX
GOOGLE_FORM_ENTRY_NAME=entry.1111111111
GOOGLE_FORM_ENTRY_EMAIL=entry.2222222222
GOOGLE_FORM_ENTRY_PHONE=entry.3333333333
GOOGLE_FORM_ENTRY_SUBJECT=entry.4444444444
GOOGLE_FORM_ENTRY_MESSAGE=entry.5555555555
GOOGLE_FORM_ENTRY_TYPE=entry.6666666666
GOOGLE_FORM_ENTRY_ITEM_TITLE=entry.7777777777
GOOGLE_FORM_ENTRY_ITEM_TYPE=entry.8888888888
DELIVERY_ASYNC=False
```

Restart Django after editing `.env`:

```bash
python manage.py runserver
```

## 6. Test the connection

```bash
python manage.py test_google_form            # shows the mapping / config check
python manage.py test_google_form --send     # posts a real test row
```

Then open the form's **Responses** tab (or **Link to Sheets**) — the test row
should appear within seconds.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `GOOGLE_FORM_ID not configured` | env var empty or server not restarted |
| `no mapped GOOGLE_FORM_ENTRY_* fields` | none of the `entry.` ids were set |
| Response 401/403/302 to a login page | form is restricted to your organisation — set **Responses → General → Collect email addresses = Off** and share it publicly |
| Row saved in DB but not in the Sheet | check the enquiry's *delivery log* in Django admin (Enquiries → open a row) |
| Nothing at all | run `python manage.py test_google_form --send` and read the printed status |

Note: visa enquiries and "Request a Call Back" requests intentionally go to
**WhatsApp**, not the Google Form. Contact-page messages go to **Gmail + Google Form**.
