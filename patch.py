import os
import glob
import shutil
import json

# 1. Patch HTML files (add noindex, strip native manifest link)
for path in glob.glob('scratch-gui/build/*.html'):
  print(f'Patching HTML {path}')
  with open(path, 'r', encoding='utf-8') as f:
    contents = f.read()
    contents = contents.replace('</head>', '<meta name="robots" content="noindex"></head>')
    contents = contents.replace('<link rel="manifest" href="manifest.webmanifest">', '')
  with open(path, 'w', encoding='utf-8') as f:
    f.write(contents)

# 2. Patch JS files (swap trampoline domains)
for path in glob.glob('scratch-gui/build/**/*.js', recursive=True):
  print(f'Patching JS {path}')
  with open(path, 'r', encoding='utf-8') as f:
    contents = f.read()
    contents = contents.replace('https://trampoline.turbowarp.org', 'https://trampoline.turbowarp.xyz')
  with open(path, 'w', encoding='utf-8') as f:
    f.write(contents)

# 3. Clean up unneeded files (Notice: sw.js removal removed so we can overwrite it)
os.remove('scratch-gui/build/manifest.webmanifest')
os.remove('scratch-gui/build/fullscreen.html')
os.remove('scratch-gui/build/index.html')

# 4. Set up final entry points
shutil.copy('scratch-gui/build/editor.html', 'scratch-gui/build/index.html')
shutil.copy('robots.txt', 'scratch-gui/build/robots.txt')

# ==============================================================================
# NEW: AUTOMATED OFFLINE CACHE GENERATION
# ==============================================================================

print("Generating offline manifest and sw.js...")

# Crawl the entire build output directory to find every single asset file
build_files = []
for root, dirs, files in os.walk('scratch-gui/build'):
    for file in files:
        full_path = os.path.join(root, file)
        # Convert system path to a web-accessible relative URL path
        relative_url = os.path.relpath(full_path, 'scratch-gui/build').replace('\\', '/')
        
        # Don't cache the service worker file itself
        if relative_url != 'sw.js':
            build_files.append('./' + relative_url)

# Turn the file list into a safely escaped JSON array string for JavaScript injection
manifest_json = json.dumps(build_files, indent=2)

# Write out a brand new sw.js file into the build directory
sw_code = f"""const CACHE_NAME = 'scratch-gui-all-offline-v1';
const ASSETS = {manifest_json};

// Install Event: Download absolutely everything into the cache immediately
self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {{
      console.log('Caching all repo assets offline...');
      // Using a map to catch individual failures gracefully if a file is missing
      return Promise.all(
        ASSETS.map(url => {{
          return cache.add(url).catch(err => console.warn('Failed to cache:', url, err));
        }})
      );
    }}).then(() => self.skipWaiting())
  );
}});

// Activate Event: Claim clients and wipe old caches
self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) => {{
      return Promise.all(keys.map(key => {{
        if (key !== CACHE_NAME) return caches.delete(key);
      }}));
    }}).then(() => self.clients.claim())
  );
}});

// Fetch Event: Cache-First strategy to ensure absolute offline functionality
self.addEventListener('fetch', (event) => {{
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {{
      // Always serve from cache if available (Offline-First)
      if (cachedResponse) {{
        return cachedResponse;
      }}
      // Fallback to network if it's a dynamic asset not caught in the build manifest
      return fetch(event.request);
    }})
  );
}});
"""

with open('scratch-gui/build/sw.js', 'w', encoding='utf-8') as f:
    f.write(sw_code)
print(f"✓ Successfully generated sw.js caching {len(build_files)} assets.")

# 5. Inject the Service Worker registration script into the newly copied index.html
index_path = 'scratch-gui/build/index.html'
with open(index_path, 'r', encoding='utf-8') as f:
    index_html = f.read()

sw_registration_script = """
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js')
        .then(reg => console.log('Offline system active:', reg.scope))
        .catch(err => console.error('Offline system failed to register:', err));
    });
  }
</script>
</body>
"""

if "</body>" in index_html:
    index_html = index_html.replace("</body>", sw_registration_script)
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("✓ Service worker successfully registered inside index.html")

