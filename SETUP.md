
---

## 14. Fixes in this build (enquiry / booking / payment)

| Problem | Fix |
|---|---|
| `POST /api/enquiries/` returned **400** `"google_form" is not a valid choice` | `google_form` added to `EnquiryChannel`; the serializer also normalises aliases (`gform`, `google forms`, `web`, …) and falls back to `form` instead of erroring. |
| Visa vs non-visa routing could disagree with the client | Server now derives `is_visa` / `channel` / `item_type` itself: `item_type=visa` (or `channel=whatsapp`) ⇒ WhatsApp only, everything else ⇒ Google Form. |
| Public submissions could set `status` / delivery flags | `status` forced to `new`; `google_form_sent`, `email_sent`, `whatsapp_url`, `delivery_log`, `ip_address` are read-only. |
| `POST /api/bookings/` returned **400** `total_amount is required` | `BookingSerializer` accepts the website's aliases: `amount → total_amount`, `item_id → item_slug`, `subject → item_title`, and resolves the package/hotel/activity/visa FK from the slug when it exists. |
| Booking lost the item context when no FK matched | New `Booking.item_slug` / `Booking.item_title` columns (migration `0002`). |
| Form submit hung when Google Forms / Gmail was slow | Delivery now runs on a background thread (`DELIVERY_ASYNC=True`). The WhatsApp deep link is still built inline, so `whatsapp_url` is in the response immediately. |
| Website called `/api/payments/adyen/create-link/` (404) | Endpoint added. It reads the **amount and currency from the stored booking**, so the price cannot be tampered with from the browser. |
| `pip install` failed on Python 3.13 | `psycopg[binary]>=3.2.2,<4`. |

Apply the new migration:

```bash
python manage.py migrate
```

---

## 15. Google Form delivery fix and verification

This build accepts either a bare Google Form ID or the complete `/viewform`
URL in `GOOGLE_FORM_ID`. The previous code appended the full URL as though it
were an ID, producing an invalid endpoint. Reliable inline delivery is now the
default because daemon threads may be stopped by production web workers.

1. Copy `.env.example` to `.env` and enter the real form and `entry.*` values.
2. Keep `DELIVERY_ASYNC=False` unless a persistent task worker is configured.
3. Restart Django after changing `.env`.
4. Run the real submission diagnostic:

```bash
python manage.py test_google_form --send
```

5. Submit an enquiry and inspect `google_form_sent` and `delivery_log` in Django
admin. Existing failed rows can be selected and retried with **Retry delivery
for selected enquiries**.

Google Form fields marked required must have a configured entry mapping and a
value in the enquiry payload. The form must remain published and accepting
responses. Visa enquiries intentionally route to the WhatsApp deep link only.

---

## 19. Image uploads (file upload → database + media folder)

Every content model (Package, Deal, Hotel, Activity, Visa, Gallery,
Testimonial, Home Hero Slide, Home Gallery Slider) now has:

| Field            | Type              | Purpose                                              |
| ---------------- | ----------------- | ---------------------------------------------------- |
| `image`          | CharField (URL)   | Read field — always returns the final absolute URL     |
| `image_file`     | ImageField        | The real uploaded file (stored in `MEDIA_ROOT`)        |
| `gallery_images` | JSON list of URLs | **Multiple images** for the same record                |

Extra pairs: `Visa.flag/flag_file`,
`Testimonial.avatar/avatar_file`, `GalleryItem.images` + `GalleryItem.videos`.

### How to send images

Post the record as `multipart/form-data`:

```bash
curl -X POST http://127.0.0.1:8000/api/packages/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "slug=dubai-5n" -F "name=Dubai 5N" -F "duration=5N/6D" -F "price=1999" \
  -F "image=@hero.jpg" \
  -F "gallery_images=@g1.jpg" -F "gallery_images=@g2.jpg" \
  -F 'gallery_images_json=["https://cdn.site.com/keep-this.jpg"]'
```

* `image` accepts **either** an uploaded file **or** a plain URL string.
* `gallery_images` accepts any number of files; `gallery_images_json` keeps the
  images that are already saved (send it whenever you edit a record).

### Standalone upload endpoint

```bash
curl -X POST http://127.0.0.1:8000/api/uploads/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" -F "file=@photo.jpg"
# => {"url": "http://127.0.0.1:8000/media/uploads/direct/ab12…_photo.jpg", "urls": [...]}
```

### Migration + media folder

```bash
python manage.py migrate            # applies api/0003_… (image_file + gallery_images)
mkdir -p media                      # MEDIA_ROOT (already gitignored)
```

Media is served at `/media/…` (`MEDIA_URL`) in development and production.
The Django admin shows a thumbnail preview (`Preview` / `Gallery` read-only
fields) and the React admin panel shows image thumbnails in every list table.
