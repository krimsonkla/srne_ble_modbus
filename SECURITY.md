# Security Policy

## Supported Versions

This project is currently in active development. Security updates will be provided for:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| develop | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**CRITICAL: Do NOT report security vulnerabilities through public GitHub issues.**

### For Security Issues

If you discover a security vulnerability, please follow these steps:

1. **DO NOT** disclose the vulnerability publicly
2. **DO NOT** create a public GitHub issue
3. **DO NOT** discuss in public forums or chat

### How to Report

Send a detailed report to the project maintainers via:

- **GitHub Security Advisory**: [Create a private security advisory](https://github.com/krimsonkla/srne_ble_modbus/security/advisories/new)
- **Email**: Contact maintainers directly (see GitHub profiles)

### What to Include

Your report should include:

1. **Description**: Detailed description of the vulnerability
2. **Impact**: Potential impact (data breach, hardware damage, etc.)
3. **Severity**: Your assessment of severity (Critical/High/Medium/Low)
4. **Steps to Reproduce**: Detailed steps to reproduce the issue
5. **Affected Versions**: Which versions are affected
6. **Suggested Fix**: If you have suggestions for fixing
7. **Your Contact**: How we can reach you for follow-up

### Example Report Template

```
Subject: [SECURITY] Brief description of issue

Description:
[Detailed description of the vulnerability]

Impact:
[Potential consequences if exploited]

Severity: [Critical/High/Medium/Low]

Steps to Reproduce:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Affected Versions:
[List affected versions]

Suggested Fix:
[Your suggestions, if any]

Contact:
[Your contact information]
```

## Safety-Critical Issues

This software controls electrical equipment. Security issues that could lead to:
- Hardware damage
- Fire hazards
- Electrical hazards
- Battery damage
- Personal injury

Should be reported as **CRITICAL** priority.

### Examples of Critical Issues

- Authentication bypass allowing unauthorized control
- Buffer overflows in Modbus protocol handling
- BLE security vulnerabilities
- Input validation failures for register writes
- Race conditions in write transactions
- Unsafe default configurations
- Missing safety checks
- Timeout bypass mechanisms

## Response Timeline

We take all security reports seriously and will respond according to severity:

- **Critical**: Initial response within 24 hours
- **High**: Initial response within 72 hours
- **Medium**: Initial response within 1 week
- **Low**: Initial response within 2 weeks

## Disclosure Policy

We follow **responsible disclosure**:

1. You report the vulnerability privately
2. We acknowledge receipt within the timeline above
3. We investigate and develop a fix
4. We release a security patch
5. After patch is available and users have time to update (typically 30 days), we publicly disclose:
   - The vulnerability details
   - Credit to the reporter (if desired)
   - The fix and affected versions

## Security Best Practices for Users

### Installation Security

1. **Network Isolation**: Isolate Home Assistant on secure network
2. **Access Control**: Use strong authentication
3. **Updates**: Keep software updated
4. **Monitoring**: Monitor logs for suspicious activity
5. **Backups**: Regular configuration backups

### BLE Security

1. **Physical Security**: BLE has limited range - control physical access
2. **Pairing**: Use secure pairing when available
3. **Monitoring**: Monitor for unauthorized connections
4. **Network**: Keep Home Assistant network separate from guest networks

### Configuration Security

1. **Validation**: Always validate configuration changes
2. **Testing**: Test changes in safe environment first
3. **Limits**: Set conservative limits on writable parameters
4. **Monitoring**: Enable all safety monitoring features
5. **Documentation**: Document your security configuration

### Operational Security

1. **Logging**: Enable comprehensive logging
2. **Alerts**: Set up alerts for critical events
3. **Review**: Regularly review logs and configurations
4. **Updates**: Subscribe to security updates
5. **Backups**: Maintain known-good configuration backups

## Known Security Considerations

### BLE Protocol Security

- **Unencrypted**: BLE communication may not be encrypted
- **Limited Range**: Physical proximity required (security by obscurity)
- **No Authentication**: Some devices lack authentication
- **Recommendation**: Physical security and network isolation

### Modbus RTU Security

- **No Built-in Security**: Modbus RTU has no authentication or encryption
- **Trust-based**: Assumes all requests are authorized
- **Recommendation**: Control access to the BLE device

### Home Assistant Integration

- **Authentication**: Relies on Home Assistant authentication
- **Authorization**: No per-entity authorization
- **Recommendation**: Secure Home Assistant installation properly

## Security Improvements

We actively work to improve security:

- Input validation on all write operations
- Transaction-based writes with rollback
- Read-verify after write operations
- Timeout mechanisms
- Error handling and logging
- Range validation against specifications

## Third-Party Dependencies

This software depends on:
- Home Assistant Core
- bleak (BLE library)
- bleak-retry-connector
- Other Python packages

Security issues in dependencies should be:
1. Reported to the dependency maintainers
2. Also reported to us if they affect our integration
3. We will update dependencies when fixes are available

## Security Acknowledgments

We thank the following researchers for responsible disclosure:

- [To be populated with security researchers who report issues]

## Questions?

For non-security questions about:
- General security best practices
- Configuration recommendations
- Safe operation guidelines

Please open a regular GitHub issue or discussion.

For actual security vulnerabilities, follow the reporting process above.

---

**Remember**: This software controls electrical equipment. Security is not just about data - it's about physical safety. Report security issues responsibly to protect all users.

**Last Updated**: February 5, 2026
