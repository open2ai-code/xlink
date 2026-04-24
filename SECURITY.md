# Security Policy / 安全策略

## Supported Versions / 支持的版本

The following versions of XLink are currently being supported with security updates:

以下版本的XLink目前支持安全更新：

| Version / 版本 | Supported / 支持状态 |
| -------------- | -------------------- |
| Latest release | ✅ Yes / 是          |
| Older versions | ❌ No / 否           |

## Reporting a Vulnerability / 报告漏洞

We take the security of XLink seriously. If you believe you have found a security vulnerability, please report it to us as described below.

我们非常重视XLink的安全性。如果您认为发现了安全漏洞，请按照以下描述报告给我们。

### Reporting Process / 报告流程

**Please do NOT report security vulnerabilities through public GitHub issues.**

**请不要通过公开的GitHub Issue报告安全漏洞。**

Instead, please report them via:

相反，请通过以下方式报告：

1. **Email / 电子邮件**: [313543530@qq.com](mailto:313543530@qq.com)
2. **GitHub Private Vulnerability Reporting / GitHub私有漏洞报告**: Use the [Security Advisories](https://github.com/open2ai-code/XLink/security/advisories) feature

### What to Include / 需要包含的信息

Please include the following information in your report:

请在您的报告中包含以下信息：

- Type of vulnerability / 漏洞类型
- Full paths of source file(s) / 源文件的完整路径
- Location of the affected source code (tag/branch/commit) / 受影响源代码的位置（标签/分支/提交）
- Step-by-step instructions to reproduce / 逐步复现说明
- Impact of the issue / 问题影响
- An explanation of who might be able to exploit it / 谁可能利用此漏洞的说明
- Whether the vulnerability is public knowledge or known to third parties / 该漏洞是否为公开信息或第三方已知

### Response Timeline / 响应时间线

- **Acknowledgment / 确认收到**: Within 48 hours / 48小时内
- **Preliminary Assessment / 初步评估**: Within 1 week / 1周内
- **Fix Development / 修复开发**: Within 2-4 weeks (depending on severity) / 2-4周内（取决于严重程度）
- **Public Disclosure / 公开披露**: After fix is released / 修复发布后

### What to Expect / 您可以期待

If your report is valid:

如果您的报告有效：

1. We will acknowledge your report within 48 hours
2. We will work on a fix and keep you updated on progress
3. We will credit you in the release notes (unless you prefer to remain anonymous)
4. We will notify you when the fix is released

1. 我们将在48小时内确认您的报告
2. 我们将致力于修复，并随时向您更新进展
3. 我们将在发布说明中感谢您（除非您希望保持匿名）
4. 我们将在修复发布时通知您

## Security Best Practices / 安全最佳实践

### For Users / 用户建议

1. **Keep XLink Updated / 保持XLink更新**
   - Always use the latest version
   - Always use the latest version
   - 始终使用最新版本

2. **Protect Your Configuration / 保护您的配置**
   - Don't share your `config/sessions.json` file
   - Don't share your `config/encryption.key` file
   - 不要分享您的`config/sessions.json`文件
   - 不要分享您的`config/encryption.key`文件

3. **Use Strong Authentication / 使用强认证**
   - Prefer SSH keys over passwords when possible
   - Use strong, unique passwords
   - 尽可能优先使用SSH密钥而非密码
   - 使用强且唯一的密码

4. **Verify Server Identity / 验证服务器身份**
   - Always verify host key fingerprints
   - Be cautious of man-in-the-middle attacks
   - 始终验证主机密钥指纹
   - 警惕中间人攻击

### For Contributors / 贡献者建议

1. **Never Commit Secrets / 绝不提交密钥**
   - Don't commit passwords, API keys, or private keys
   - Use environment variables for sensitive data
   - 不要提交密码、API密钥或私钥
   - 对环境变量使用敏感数据

2. **Review Code for Security Issues / 审查代码安全性**
   - Check for injection vulnerabilities
   - Validate all user inputs
   - 检查注入漏洞
   - 验证所有用户输入

3. **Follow Secure Coding Guidelines / 遵循安全编码指南**
   - Use parameterized queries
   - Implement proper error handling
   - 使用参数化查询
   - 实施适当的错误处理

## Security Features / 安全特性

XLink includes several security features:

XLink包含多项安全特性：

- **Password Encryption / 密码加密**: Stored passwords are encrypted using Fernet symmetric encryption
- **SSH Key Support / SSH密钥支持**: Supports RSA, DSA, ECDSA, and Ed25519 private keys
- **Host Key Verification / 主机密钥验证**: Verifies server host keys to prevent MITM attacks
- **Secure Configuration / 安全配置**: Sensitive configuration files are excluded from version control

## Known Security Limitations / 已知安全限制

1. Passwords are encrypted but the encryption key is stored locally
2. Host key verification is not yet fully implemented
3. No built-in support for certificate-based authentication

1. 密码已加密，但加密密钥存储在本地
2. 主机密钥验证尚未完全实现
3. 不支持基于证书的认证

## Security Updates / 安全更新

Security updates will be released as:

安全更新将作为以下形式发布：

- Patch releases for critical vulnerabilities
- Regular releases for non-critical security improvements
- Security advisories on GitHub

- 关键漏洞的补丁发布
- 非关键安全改进的常规发布
- GitHub上的安全公告

## Acknowledgments / 致谢

We appreciate security researchers and contributors who responsibly disclose vulnerabilities to help keep XLink and its users safe.

我们感谢负责任地披露漏洞以帮助保护XLink及其用户的安全研究人员和贡献者。

---

**Last Updated / 最后更新**: 2026-04-23
