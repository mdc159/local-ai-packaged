# Dashy Dashboard Customization Guide

This guide explains how to customize the Dashy dashboard for your local AI stack.

## Configuration File Location

The main configuration file is located at: `dashy/dashy-conf.yml`

## Basic Configuration Structure

```yaml
appConfig:        # Global app settings
pageInfo:         # Page metadata and navigation
sections:         # Service tiles organized by category
```

## Customizing Themes

### Available Themes
Dashy includes 20+ built-in themes. Popular options include:
- `nord-frost` (current default)
- `dracula`
- `material`
- `matrix`
- `cyberpunk`
- `minimal-light`
- `minimal-dark`

To change the theme, edit `dashy-conf.yml`:
```yaml
appConfig:
  theme: dracula  # Change to your preferred theme
```

## Adding New Services

To add a new service tile, add an entry under the appropriate section:

```yaml
sections:
- name: Your Section Name
  items:
  - title: Service Name
    description: Brief description
    icon: https://url-to-icon.png  # Or use Font Awesome: fas fa-icon-name
    url: https://service-url.com
    statusCheckUrl: https://service-url.com/health  # Optional health check
    tags: [tag1, tag2]  # Optional tags for filtering
    statusCheckAcceptCodes: "200,201,301"  # HTTP codes to consider healthy
```

## Icon Options

You can use various icon sources:

1. **Direct URLs**:
   ```yaml
   icon: https://example.com/icon.png
   ```

2. **Font Awesome Icons**:
   ```yaml
   icon: fas fa-robot  # Font Awesome solid
   icon: fab fa-github # Font Awesome brand
   ```

3. **Local Icons**:
   Place icons in `dashy/icons/` and reference them:
   ```yaml
   icon: /item-icons/my-icon.png
   ```

## Status Monitoring

### Enable/Disable Status Checks
```yaml
appConfig:
  statusCheck: true  # Set to false to disable all checks
  statusCheckInterval: 60  # Check interval in seconds
```

### Configure Individual Service Checks
```yaml
items:
- title: My Service
  statusCheckUrl: https://service.com/health
  statusCheckAcceptCodes: "200,301,302"  # Accepted HTTP status codes
  statusCheckMaxRedirects: 2  # Max redirects to follow
```

## Layout Options

### Grid Layout
```yaml
appConfig:
  layout: auto  # Options: auto, horizontal, vertical
  iconSize: medium  # Options: small, medium, large
```

### Sections Layout
```yaml
sections:
- name: Section Name
  displayData:
    cols: 2  # Number of columns for this section
    collapsed: false  # Start collapsed or expanded
    hideForGuests: false  # Hide from non-authenticated users
```

## Authentication (Optional)

To add authentication to your dashboard:

```yaml
appConfig:
  auth:
    enableGuestAccess: true
    users:
    - username: admin
      password: $2a$12$hashedpasswordhere  # Use bcrypt hash
      type: admin
```

Generate password hash:
```bash
docker exec -it dashy yarn bcrypt-hash "yourpassword"
```

## Environment-Specific Configuration

You can use environment variables in your configuration:

```yaml
pageInfo:
  title: ${DASHBOARD_TITLE:-AI Stack Dashboard}

items:
- title: n8n
  url: https://${N8N_HOSTNAME:-n8n.local}
```

## Advanced Customization

### Custom CSS
Add custom styles in `appConfig`:
```yaml
appConfig:
  customCss: |
    .item { border-radius: 10px; }
    .section-title { color: #3498db; }
```

### Search Options
```yaml
appConfig:
  enableSearchBar: true
  searchEngine: duckduckgo  # Options: google, duckduckgo, bing, etc.
```

### Keyboard Shortcuts
```yaml
appConfig:
  enableKeyboardShortcuts: true
```

Default shortcuts:
- `/` - Focus search bar
- `Esc` - Close modals
- `Alt + [number]` - Quick launch items

## Applying Changes

After editing `dashy-conf.yml`:

1. **Restart Dashy container**:
   ```bash
   docker compose -p localai restart dashy
   ```

2. **Or reload configuration** (if Dashy is running):
   - Visit your dashboard
   - Press `Ctrl + R` or click the refresh icon

## Backup Configuration

Always backup your configuration before major changes:
```bash
cp dashy/dashy-conf.yml dashy/dashy-conf.yml.backup
```

## Troubleshooting

### Configuration Not Loading
- Check YAML syntax (use a YAML validator)
- Ensure proper indentation (2 spaces, not tabs)
- Check container logs: `docker compose -p localai logs dashy`

### Icons Not Displaying
- Verify icon URLs are accessible
- Check CORS policies for external icons
- Use local icons in `dashy/icons/` for reliability

### Status Checks Failing
- Verify `statusCheckUrl` is correct
- Ensure `statusCheckAcceptCodes` includes all valid response codes
- Check if services are accessible from Dashy container

## Example Configurations

### Minimal Configuration
```yaml
pageInfo:
  title: My Dashboard
sections:
- name: Services
  items:
  - title: Service 1
    url: http://service1.local
```

### Full-Featured Configuration
See the current `dashy/dashy-conf.yml` for a complete example with all services configured.

## Resources

- [Dashy Documentation](https://dashy.to/docs/)
- [Dashy GitHub](https://github.com/Lissy93/dashy)
- [Icon Sources](https://fontawesome.com/icons)
- [Theme Gallery](https://dashy.to/docs/theming/)