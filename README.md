# ფოტო ანიმაცია

ფოტოს ცოცხალ კადრად გადაქცევა — ნელი Ken Burns ზუმი, ოქროს შუქის ციმციმი და სიგარეტის კვამლის ეფექტი.

## დემო

გახსენი `public/index.html` ბრაუზერში, ან გაუშვი:

```bash
python3 -m http.server 8080 --directory public
```

შემდეგ გახსენი http://localhost:8080

- ატვირთე საკუთარი ფოტო
- დაარეგულირე კვამლი / ზუმი / შუქი
- ჩაწერე WebM ვიდეო

## CLI ანიმაცია

```bash
pip install pillow imageio imageio-ffmpeg
python3 scripts/animate_photo.py \
  --src public/cafe-photo.png \
  --out-mp4 public/cafe-animation.mp4 \
  --out-gif public/cafe-animation.gif
```

მზა დემო ფაილები: `public/cafe-animation.mp4`, `public/cafe-animation.gif`
