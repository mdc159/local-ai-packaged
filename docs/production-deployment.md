# Production Deployment Guide

This guide covers deploying the local-ai-packaged stack to a production environment with proper security and configuration.

## Prerequisites

- Linux server (Ubuntu recommended)
- Docker and Docker Compose installed
- Domain name with DNS management access
- SSL certificates (handled automatically by Caddy)

## Initial Server Setup

### 1. System Requirements
- **Minimum**: 8GB RAM, 4 CPU cores, 100GB storage
- **Recommended**: 16GB RAM, 8 CPU cores, 200GB storage
- **GPU** (optional): NVIDIA GPU for local LLM inference

### 2. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Python 3 and Git
sudo apt install python3 python3-pip git nano -y
```

### 3. Configure Firewall
```bash
# Enable firewall
sudo ufw enable

# Allow SSH (adjust port if needed)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Reload firewall
sudo ufw reload
```

**WARNING**: Docker bypasses UFW rules. The production environment configuration ensures only ports 80/443 are exposed.

## Deployment Steps

### 1. Clone Repository
```bash
git clone -b stable https://github.com/mdc159/local-ai-packaged.git
cd local-ai-packaged
```

### 2. Configure Environment
```bash
# Copy example environment
cp .env.example .env

# Edit environment file
nano .env
```

**Critical Settings:**
- Generate secure secrets for all keys
- Set strong passwords for all services
- Update `NEO4J_AUTH=neo4j/your_secure_password`
- Set domain-specific variables

### 3. Configure Domain Names

Add to `.env`:
```bash
# Production domains
N8N_HOSTNAME=n8n.yourdomain.com
WEBUI_HOSTNAME=openwebui.yourdomain.com
FLOWISE_HOSTNAME=flowise.yourdomain.com
SUPABASE_HOSTNAME=supabase.yourdomain.com
LANGFUSE_HOSTNAME=langfuse.yourdomain.com
SEARXNG_HOSTNAME=searxng.yourdomain.com
NEO4J_HOSTNAME=neo4j.yourdomain.com

# Email for Let's Encrypt SSL certificates
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

### 4. Configure DNS

Create A records pointing to your server IP:
- `yourdomain.com` → Server IP (for Dashy dashboard)
- `n8n.yourdomain.com` → Server IP
- `openwebui.yourdomain.com` → Server IP
- `flowise.yourdomain.com` → Server IP
- `supabase.yourdomain.com` → Server IP
- `langfuse.yourdomain.com` → Server IP
- `searxng.yourdomain.com` → Server IP
- `neo4j.yourdomain.com` → Server IP

### 5. Deploy Services

```bash
# Deploy with appropriate GPU profile and public environment
# For NVIDIA GPU:
python3 start_services.py --profile gpu-nvidia --environment public

# For AMD GPU:
python3 start_services.py --profile gpu-amd --environment public

# For CPU only:
python3 start_services.py --profile cpu --environment public

# For external Ollama:
python3 start_services.py --profile none --environment public
```

**Important**: The `--environment public` flag:
- Closes all ports except 80 and 443
- Ensures services are only accessible through Caddy reverse proxy
- Enables production security settings

## Post-Deployment

### 1. Verify Services
```bash
# Check all services are running
docker compose -p localai ps

# Monitor logs
docker compose -p localai logs -f

# Test service endpoints
curl -I https://yourdomain.com
curl -I https://n8n.yourdomain.com
```

### 2. Initial Configuration

#### Dashy Dashboard
- Access at `https://yourdomain.com`
- No additional setup required
- Edit `dashy/dashy-conf.yml` to customize

#### n8n
1. Access at `https://n8n.yourdomain.com`
2. Create admin account on first access
3. Import workflows from `n8n/backup/workflows/`

#### Open WebUI
1. Access at `https://openwebui.yourdomain.com`
2. Create admin account on first access
3. Configure n8n integration function

#### Flowise
1. Access at `https://flowise.yourdomain.com`
2. Login with credentials from `.env`
3. Import chatflows from `flowise/` directory

## Security Considerations

### SSL/TLS
- Caddy automatically obtains and renews Let's Encrypt certificates
- All services are accessed via HTTPS
- HTTP automatically redirects to HTTPS

### Network Security
- Only ports 80/443 are exposed externally
- Inter-service communication uses Docker internal network
- Services cannot be accessed directly from outside

### Authentication
- Each service has its own authentication mechanism
- Use strong, unique passwords for each service
- Enable 2FA where available (n8n, Supabase)

### Backup Strategy
```bash
# Backup configurations
tar -czf backup-config-$(date +%Y%m%d).tar.gz .env docker-compose.yml dashy/ n8n/backup/ flowise/

# Backup Docker volumes
docker run --rm -v localai_n8n_storage:/data -v $(pwd):/backup alpine tar czf /backup/n8n-data-$(date +%Y%m%d).tar.gz -C /data .

# Backup database
docker exec supabase-db pg_dump -U postgres postgres > backup-db-$(date +%Y%m%d).sql
```

## Maintenance

### Updates
```bash
# Pull latest changes
git pull origin stable

# Update containers
docker compose -p localai pull

# Restart services
python3 start_services.py --profile <your-profile> --environment public
```

### Monitoring
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Monitor container resources
docker stats

# Check service logs for errors
docker compose -p localai logs --tail=100 | grep ERROR
```

### Troubleshooting Production Issues

#### Services Not Accessible
1. Check DNS propagation: `nslookup subdomain.yourdomain.com`
2. Verify Caddy is running: `docker compose -p localai ps caddy`
3. Check Caddy logs: `docker compose -p localai logs caddy`
4. Verify SSL certificates: `docker exec caddy caddy list-certificates`

#### SSL Certificate Issues
- Ensure DNS is properly configured before starting services
- Check rate limits (Let's Encrypt has limits)
- Verify email in LETSENCRYPT_EMAIL is valid

#### Performance Issues
- Scale services: Edit `docker-compose.yml` to add replicas
- Increase resource limits in Docker
- Use external databases for production workloads

## Scaling Considerations

### Database
- Consider external PostgreSQL for production
- Use managed services (AWS RDS, Google Cloud SQL) for reliability
- Regular backups and replication

### Storage
- Use object storage (S3, MinIO) for file storage
- Mount network storage for shared data
- Regular cleanup of temporary files

### Load Balancing
- Use external load balancer for high availability
- Deploy multiple instances behind load balancer
- Session persistence for stateful services

## Support

- GitHub Issues: https://github.com/mdc159/local-ai-packaged/issues
- Documentation: This guide and README.md
- Community: Local AI forum at https://thinktank.ottomator.ai/c/local-ai/18