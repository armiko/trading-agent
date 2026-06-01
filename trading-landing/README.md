# AI Trading Agent - Landing Page

Landing page untuk AI Trading Agent project.

## 📁 Files

- `index.html` - Main landing page (single page, responsive)

## 🚀 Quick Start

### Local Development

1. **Open directly in browser:**
   ```bash
   open index.html
   # atau
   firefox index.html
   # atau
   chrome index.html
   ```

2. **Using Python HTTP Server:**
   ```bash
   cd trading-landing
   python -m http.server 8000
   # Buka http://localhost:8000
   ```

3. **Using Node.js HTTP Server:**
   ```bash
   npx http-server
   # Buka http://localhost:8080
   ```

## 🎨 Features

### Design
- **Modern gradient design** (purple/blue theme)
- **Fully responsive** (mobile, tablet, desktop)
- **Smooth animations** on hover and scroll
- **Clean typography** with Segoe UI font
- **Single page layout** with smooth scrolling

### Sections
1. **Hero Section** - Main headline with CTA button
2. **Features Grid** - 9 advanced features with icons
3. **Tech Stack** - Technology overview
4. **Architecture Diagram** - System architecture visualization
5. **Stats Section** - Key metrics and capabilities
6. **CTA Section** - GitHub link and call-to-action
7. **Footer** - Links and credits

## 🌐 Deployment Options

### GitHub Pages

1. **Create gh-pages branch:**
   ```bash
   git checkout -b gh-pages
   git add trading-landing/
   git commit -m "Add landing page"
   git push origin gh-pages
   ```

2. **Enable GitHub Pages:**
   - Go to repository Settings
   - Navigate to Pages
   - Select `gh-pages` branch
   - Set folder to `/trading-landing`
   - Save

3. **Access at:**
   ```
   https://armiko.github.io/trading-agent/
   ```

### Netlify

1. **Drag & drop:**
   - Go to https://app.netlify.com/drop
   - Drag `trading-landing` folder
   - Done!

2. **Or via CLI:**
   ```bash
   npm install -g netlify-cli
   cd trading-landing
   netlify deploy
   ```

### Vercel

```bash
npm install -g vercel
cd trading-landing
vercel
```

### Cloudflare Pages

1. Go to Cloudflare Pages dashboard
2. Create new project
3. Connect GitHub repository
4. Set build directory to `trading-landing`
5. Deploy

## 🎯 Customization

### Colors

Edit CSS variables in `<style>` section:

```css
/* Primary gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to your colors */
background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
```

### Content

1. **Hero Section:**
   - Edit `<header>` section
   - Change title, subtitle, CTA text

2. **Features:**
   - Edit `.feature-card` divs
   - Change icons (emoji), titles, descriptions

3. **Tech Stack:**
   - Edit `.tech-item` divs
   - Add/remove technologies

4. **Architecture:**
   - Edit `<pre>` content in `.architecture-diagram`
   - Update ASCII diagram

5. **Stats:**
   - Edit `.stat-card` divs
   - Change numbers and labels

### Links

Update GitHub links:

```html
<!-- Change all instances of -->
href="https://github.com/armiko/trading-agent"

<!-- To your repository -->
href="https://github.com/YOUR_USERNAME/YOUR_REPO"
```

## 📱 Responsive Breakpoints

- **Desktop:** > 768px (3-column grid)
- **Tablet:** 768px (2-column grid)
- **Mobile:** < 768px (1-column grid)

## 🔧 Browser Support

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 📊 Performance

- **No external dependencies** (pure HTML/CSS)
- **No JavaScript** (static page)
- **Fast load time** (< 50KB)
- **SEO friendly** (semantic HTML)

## 🎨 Design Credits

- **Color Scheme:** Purple/Blue gradient
- **Icons:** Emoji (universal support)
- **Typography:** Segoe UI (system font)
- **Layout:** CSS Grid + Flexbox

## 📝 License

Same as main project (open source).

## 🤝 Contributing

To improve the landing page:

1. Fork the repository
2. Edit `trading-landing/index.html`
3. Test locally
4. Submit pull request

## 📞 Support

For issues or suggestions:
- Open an issue on GitHub
- Contact: [Your contact info]

---

**Built with ❤️ for AI Trading Agent**
