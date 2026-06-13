---
name: image-creation
description: Generate images using AI image generation APIs (DALL-E/OpenAI). Use when the user asks to create, generate, or produce an image — including book covers, illustrations, artwork, diagrams, or any visual content. Pass the image description as args.
---

# Image Creation Skill

Generate images from text prompts using DALL-E (OpenAI) and save them to the local filesystem.

## Workflow

### 1. Determine the Prompt

If `args` was provided, use it as the image prompt. Otherwise ask the user:
- What should the image show?
- Any style preferences (photorealistic, illustration, watercolor, etc.)?
- Intended use (book cover, profile picture, diagram, etc.)?

For book cover generation in the bookshelf app, enrich the prompt with:
- Title and author
- Genre/mood
- Color palette or aesthetic preferences

### 2. Choose Output Location

Default output directory: current working directory or `./generated_images/`.
Create the directory if it doesn't exist.

Use a descriptive filename based on the prompt (snake_case, max 50 chars, `.png` extension).

### 3. Generate the Image

Use Python with the `openai` library. The project uses `openai==0.28.1` (legacy API style):

```python
import openai
import httpx
import os
from pathlib import Path

# Set API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Generate image
response = openai.Image.create(
    prompt="<the image prompt>",
    n=1,
    size="1024x1024"   # Options: "256x256", "512x512", "1024x1024"
)

image_url = response["data"][0]["url"]

# Download and save
output_path = Path("<output_path>")
output_path.parent.mkdir(parents=True, exist_ok=True)

with httpx.Client() as client:
    img_data = client.get(image_url).content

output_path.write_bytes(img_data)
print(f"Image saved to: {output_path}")
```

Run this as a Bash command using `python3 -c "..."` or write it to a temp script and execute it.

Check for `OPENAI_API_KEY` in the environment first:
```bash
echo "API key set: ${OPENAI_API_KEY:+yes}${OPENAI_API_KEY:-no}"
```

If the key is missing, instruct the user to set it:
```
export OPENAI_API_KEY=sk-...
```

### 4. Handle Errors

Common errors:
- `AuthenticationError` — API key missing or invalid. Ask user to set `OPENAI_API_KEY`.
- `InvalidRequestError: billing` — Account has no credits. Direct user to https://platform.openai.com/account/billing.
- `InvalidRequestError: content_policy` — Prompt violates policy. Ask user to rephrase.
- `RateLimitError` — Too many requests. Wait 10s and retry once.

### 5. Report Result

After successful generation:
- Print the absolute path to the saved image
- Describe what was generated
- If running in the bookshelf app context, suggest how the image can be used (e.g., as a book cover via the UI or API)

## Size Guide

| Use Case | Recommended Size |
|---|---|
| Book cover | 512x512 or 1024x1024 |
| Profile picture | 256x256 |
| Banner/hero image | 1024x1024 (crop after) |
| Thumbnail | 256x256 |

## Bookshelf App Context

When generating book covers for books in the bookshelf app:
1. Ask for the book title and author if not provided
2. Look up the book in the app to get genre/description context
3. Generate a cover image in `./backend/static/covers/` (create if needed)
4. Suggest updating the book record with the cover image path via the API

## Example Prompts

Good image prompts are specific and descriptive:
- "A moody hardcover book cover for a mystery novel titled 'The Last Signal', dark blue and gray tones, fog, vintage typography"
- "Minimalist illustration of a person reading under a tree at golden hour, flat design, warm colors"
- "Watercolor painting of a cozy library with floor-to-ceiling bookshelves, warm lighting, cats sleeping on chairs"
