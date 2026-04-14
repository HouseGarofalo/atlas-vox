#!/usr/bin/env bash
# Atlas Vox — Generate self-signed SSL certificates for HTTPS
#
# Usage:
#   bash scripts/generate-certs.sh                        # defaults (localhost + common LAN IPs)
#   bash scripts/generate-certs.sh myhost.local 192.168.1.50  # custom SANs
#
# Output: docker/certs/selfsigned.crt + selfsigned.key
# Browsers will show a security warning for self-signed certs — accept it once.
# For production, replace these files with real certificates (e.g., Let's Encrypt).

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$PROJECT_ROOT/docker/certs"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[atlas-vox]${NC} $1"; }
warn() { echo -e "${YELLOW}[atlas-vox]${NC} $1"; }

# Check for openssl
if ! command -v openssl &>/dev/null; then
  echo "Error: openssl is required. Install it first."
  echo "  Windows: winget install ShiningLight.OpenSSL.Light"
  echo "  macOS:   brew install openssl"
  echo "  Linux:   sudo apt install openssl"
  exit 1
fi

# Create certs directory
mkdir -p "$CERT_DIR"

# Build Subject Alternative Names from args (or defaults)
SANS="DNS:localhost,IP:127.0.0.1,IP:0.0.0.0"
if [ $# -gt 0 ]; then
  for arg in "$@"; do
    # Auto-detect IP vs hostname
    if [[ "$arg" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      SANS="$SANS,IP:$arg"
    else
      SANS="$SANS,DNS:$arg"
    fi
  done
else
  # Try to auto-detect the machine's LAN IP
  LAN_IP=""
  if command -v hostname &>/dev/null; then
    LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
  fi
  if [ -z "$LAN_IP" ] && command -v ipconfig &>/dev/null; then
    LAN_IP=$(ipconfig 2>/dev/null | grep -oP 'IPv4 Address.*?: \K[\d.]+' | head -1 || true)
  fi
  if [ -n "$LAN_IP" ]; then
    SANS="$SANS,IP:$LAN_IP"
    log "Auto-detected LAN IP: $LAN_IP"
  fi
fi

log "Generating self-signed certificate..."
log "SANs: $SANS"

# Use a config file to avoid Git Bash/MSYS path mangling of -subj argument
TMPCONF="$CERT_DIR/_openssl.cnf"
cat > "$TMPCONF" <<ENDCNF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_ext

[dn]
C = US
ST = Local
L = Local
O = AtlasVox
OU = Dev
CN = atlas-vox

[v3_ext]
subjectAltName = $SANS
keyUsage = digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:FALSE
ENDCNF

# Generate key + certificate (valid for 365 days)
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERT_DIR/selfsigned.key" \
  -out "$CERT_DIR/selfsigned.crt" \
  -days 365 \
  -config "$TMPCONF" \
  2>/dev/null

rm -f "$TMPCONF"

echo ""
log "Certificates generated:"
echo -e "  ${CYAN}$CERT_DIR/selfsigned.crt${NC}  (certificate)"
echo -e "  ${CYAN}$CERT_DIR/selfsigned.key${NC}  (private key)"
echo ""
log "Certificate details:"
openssl x509 -in "$CERT_DIR/selfsigned.crt" -noout -dates -subject -ext subjectAltName 2>/dev/null | sed 's/^/  /'
echo ""
warn "Self-signed certs will trigger a browser warning."
warn "Accept the warning once, or import the .crt into your OS trust store."
echo ""
log "To add custom hostnames or IPs, run:"
echo "  bash scripts/generate-certs.sh myhost.local 192.168.1.50"
echo ""
log "To use real certificates (Let's Encrypt, etc.):"
echo "  Replace docker/certs/selfsigned.crt and selfsigned.key with your own files."
