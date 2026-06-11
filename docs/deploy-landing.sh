#!/usr/bin/env bash
# =============================================================================
# ChinaCrawl Landing Page 部署脚本
# 将 chinacrawl/docs/index.html 部署到 47.236.24.76:7777/chinacrawl
#
# 用法:
#   ./deploy-landing.sh              # 使用默认配置
#   DRY_RUN=1 ./deploy-landing.sh    # 仅预览，不实际部署
#   FULL_DEPLOY=1 ./deploy-landing.sh # 全量部署 docs/ 目录下所有静态资源
#
# 环境变量 (可选):
#   SSH_HOST     - 目标服务器地址 (默认: 47.236.24.76)
#   SSH_USER     - SSH 用户名 (默认: root)
#   SSH_PORT     - SSH 端口 (默认: 22)
#   REMOTE_DIR   - 远程部署目录 (默认: /var/www/chinacrawl)
#   LANDING_URL  - 验证 URL (默认: http://47.236.24.76:7777/chinacrawl/)
#   DRY_RUN      - 设为 1 仅预览
#   FULL_DEPLOY  - 设为 1 部署整个 docs/ 目录
# =============================================================================

set -euo pipefail

# ── 配置 ────────────────────────────────────────────────────────────────────
SSH_HOST="${SSH_HOST:-47.236.24.76}"
SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
REMOTE_DIR="${REMOTE_DIR:-/var/www/chinacrawl}"
LANDING_URL="${LANDING_URL:-http://47.236.24.76:7777/chinacrawl/}"
DRY_RUN="${DRY_RUN:-0}"
FULL_DEPLOY="${FULL_DEPLOY:-0}"

# 脚本所在目录 → chinacrawl/docs/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"  # docs/ 目录本身
LOCAL_INDEX="$SOURCE_DIR/index.html"

SSH_TARGET="${SSH_USER}@${SSH_HOST}"
SSH_OPTS="-p ${SSH_PORT} -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
SCP_OPTS="-P ${SSH_PORT} -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"

# ── 颜色输出 ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[FAIL]${NC}  $*"; }

# ── 前置检查 ────────────────────────────────────────────────────────────────
preflight() {
    info "前置检查..."

    # 检查 index.html 是否存在
    if [[ ! -f "$LOCAL_INDEX" ]]; then
        error "找不到 $LOCAL_INDEX"
        exit 1
    fi
    success "源文件: $LOCAL_INDEX"

    # 检查 SSH 连通性
    info "检查 SSH 连通性 ($SSH_TARGET)..."
    if ! ssh $SSH_OPTS "$SSH_TARGET" "echo ok" &>/dev/null; then
        error "SSH 连接失败: $SSH_TARGET"
        warn "请确认:"
        warn "  1. 服务器可达: ping $SSH_HOST"
        warn "  2. SSH 密钥已配置或密码可用"
        warn "  3. 可设置 SSH_HOST / SSH_USER / SSH_PORT 覆盖默认值"
        exit 1
    fi
    success "SSH 连接正常"

    # 检查远程目录
    info "检查远程目录 $REMOTE_DIR..."
    if ! ssh $SSH_OPTS "$SSH_TARGET" "test -d $REMOTE_DIR" &>/dev/null; then
        warn "远程目录 $REMOTE_DIR 不存在，将自动创建"
    else
        success "远程目录已存在"
    fi
}

# ── 部署 ────────────────────────────────────────────────────────────────────
deploy() {
    if [[ "$DRY_RUN" == "1" ]]; then
        info "[DRY RUN] 以下文件将被上传到 $SSH_TARGET:$REMOTE_DIR/"
        if [[ "$FULL_DEPLOY" == "1" ]]; then
            find "$SOURCE_DIR" -type f -not -path '*/.git/*' -not -name '*.md' -not -name '*.sh' | while read -r f; do
                echo "  → ${f#$SOURCE_DIR/}"
            done
        else
            echo "  → index.html"
        fi
        return
    fi

    # 确保远程目录存在
    ssh $SSH_OPTS "$SSH_TARGET" "mkdir -p $REMOTE_DIR"

    if [[ "$FULL_DEPLOY" == "1" ]]; then
        info "全量部署 docs/ 目录..."
        rsync -avz --delete \
            --exclude='.git/' \
            --exclude='*.md' \
            --exclude='*.sh' \
            --exclude='*.ps1' \
            -e "ssh $SSH_OPTS" \
            "$SOURCE_DIR/" \
            "$SSH_TARGET:$REMOTE_DIR/"
        success "全量同步完成"
    else
        info "部署 index.html..."
        scp $SCP_OPTS "$LOCAL_INDEX" "$SSH_TARGET:$REMOTE_DIR/index.html"
        success "index.html 部署完成"
    fi
}

# ── 验证 ────────────────────────────────────────────────────────────────────
verify() {
    if [[ "$DRY_RUN" == "1" ]]; then
        info "[DRY RUN] 跳过验证"
        return
    fi

    info "验证部署..."

    # HTTP 状态码
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$LANDING_URL" 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]]; then
        success "Landing Page 返回 200 OK"
    elif [[ "$http_code" == "301" || "$http_code" == "302" ]]; then
        local redirect_url
        redirect_url=$(curl -s -o /dev/null -w "%{redirect_url}" --max-time 10 "$LANDING_URL" 2>/dev/null)
        warn "返回 $http_code 重定向 → $redirect_url"
    else
        error "返回 HTTP $http_code"
        warn "检查:"
        warn "  1. Web 服务器是否运行: ssh $SSH_TARGET 'systemctl status nginx'"
        warn "  2. 站点配置是否正确"
        warn "  3. 文件权限: ssh $SSH_TARGET 'ls -la $REMOTE_DIR/'"
    fi

    # 内容校验
    local title
    title=$(curl -s --max-time 10 "$LANDING_URL" 2>/dev/null | grep -oP '<title>\K[^<]+' || echo "")
    if [[ -n "$title" ]]; then
        success "页面标题: $title"
    else
        warn "无法读取页面标题"
    fi

    # 文件大小对比
    local local_size remote_size
    local_size=$(stat -c%s "$LOCAL_INDEX" 2>/dev/null || stat -f%z "$LOCAL_INDEX" 2>/dev/null || echo 0)
    remote_size=$(ssh $SSH_OPTS "$SSH_TARGET" "stat -c%s $REMOTE_DIR/index.html 2>/dev/null || echo 0")
    if [[ "$local_size" == "$remote_size" ]]; then
        success "文件大小一致: ${local_size} bytes"
    else
        warn "文件大小不一致 — 本地: ${local_size}, 远程: ${remote_size}"
    fi
}

# ── Web 服务检查与重启 ──────────────────────────────────────────────────────
restart_web() {
    info "检查 Web 服务..."

    # 尝试 nginx
    if ssh $SSH_OPTS "$SSH_TARGET" "command -v nginx &>/dev/null"; then
        if ssh $SSH_OPTS "$SSH_TARGET" "systemctl is-active --quiet nginx 2>/dev/null"; then
            info "nginx 运行中，reload..."
            ssh $SSH_OPTS "$SSH_TARGET" "systemctl reload nginx || systemctl restart nginx"
            success "nginx reloaded"
        else
            warn "nginx 未运行，尝试启动..."
            ssh $SSH_OPTS "$SSH_TARGET" "systemctl start nginx"
            success "nginx started"
        fi
    # 尝试 apache2
    elif ssh $SSH_OPTS "$SSH_TARGET" "command -v apache2 &>/dev/null"; then
        ssh $SSH_OPTS "$SSH_TARGET" "systemctl reload apache2 || systemctl restart apache2"
        success "apache2 reloaded"
    else
        warn "未检测到 nginx 或 apache2，跳过 Web 服务重载"
    fi
}

# ── 主流程 ──────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║   ChinaCrawl Landing Page 部署脚本               ║"
    echo "║   目标: $LANDING_URL   ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""

    if [[ "$DRY_RUN" == "1" ]]; then
        warn "*** DRY RUN 模式 — 不会实际修改任何文件 ***"
        echo ""
    fi

    preflight
    echo ""
    deploy
    echo ""

    if [[ "$DRY_RUN" != "1" ]]; then
        restart_web
        echo ""
    fi

    verify
    echo ""

    if [[ "$DRY_RUN" != "1" ]]; then
        success "部署流程完成! 访问: $LANDING_URL"
    else
        info "DRY RUN 完成，使用以下命令实际部署:"
        echo "  ./deploy-landing.sh"
    fi
}

main "$@"
