# DISCLAIMER AND TERMS OF USE

## CRITICAL SAFETY WARNING

**READ THIS ENTIRE DOCUMENT BEFORE USING THIS SOFTWARE**

This software controls electrical equipment through Bluetooth Low Energy (BLE) communication. Improper use can result in:
- Equipment damage or destruction
- Fire or electrical hazards
- Battery damage or thermal runaway
- Voided warranties
- Personal injury or death
- Property damage

## NO WARRANTY

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.

THE AUTHORS, CONTRIBUTORS, AND DISTRIBUTORS MAKE NO REPRESENTATIONS OR
WARRANTIES ABOUT THE SUITABILITY, RELIABILITY, AVAILABILITY, TIMELINESS,
SECURITY, OR ACCURACY OF THIS SOFTWARE.

## USE AT YOUR OWN RISK

This software interfaces with hardware devices (SRNE inverters and battery management systems) via Bluetooth Low Energy (BLE) and Modbus protocols.

### POTENTIAL RISKS AND HAZARDS

**Electrical Hazards:**
- High voltage DC systems (up to 400V or more)
- Risk of electric shock
- Arc flash potential
- Fire hazards from electrical faults

**Equipment Damage:**
- Inverter malfunction or damage
- Battery management system (BMS) damage
- Battery cell damage or imbalance
- BLE communication module damage
- Connected load damage

**Battery-Specific Risks:**
- Thermal runaway
- Fire or explosion
- Toxic gas release
- Shortened battery lifespan
- Complete battery failure

**Data and System Risks:**
- Data corruption
- Configuration errors
- System instability
- Communication failures
- Incorrect readings leading to poor decisions

**Safety System Risks:**
- Disabled or bypassed safety features
- Incorrect setpoints
- Failed emergency shutdowns
- Monitoring system failures

## USER RESPONSIBILITIES

### Before Using This Software

You are solely responsible for:

1. **Understanding Your Equipment:**
   - Complete knowledge of your inverter specifications
   - Understanding of battery chemistry and limitations
   - Familiarity with BLE and Modbus protocols
   - Knowledge of your system's electrical configuration

2. **Safety Precautions:**
   - Installing appropriate circuit protection
   - Having fire suppression equipment available
   - Following all local electrical codes and regulations
   - Ensuring proper ventilation for battery systems
   - Installing smoke and gas detectors
   - Having emergency shutdown procedures in place

3. **Testing and Validation:**
   - Testing in a controlled, safe environment first
   - Validating all configuration parameters
   - Monitoring system behavior continuously
   - Having backup systems in place
   - Documenting your configuration

4. **Technical Competence:**
   - Understanding of electrical systems
   - Experience with battery management
   - Familiarity with Home Assistant
   - Knowledge of BLE communication protocols
   - Ability to troubleshoot problems safely

5. **Ongoing Monitoring:**
   - Regular system inspections
   - Continuous monitoring of battery health
   - Logging and reviewing error conditions
   - Updating software and documentation
   - Maintaining safety equipment

## SPECIFIC WARNINGS

### Battery Systems
- **NEVER** modify battery charge/discharge parameters without complete understanding
- **NEVER** exceed manufacturer specifications
- **NEVER** disable battery protection features
- **ALWAYS** monitor battery temperature
- **ALWAYS** follow manufacturer safety guidelines

### Inverter Systems
- **NEVER** modify settings while under load without proper protection
- **NEVER** disable overcurrent or overvoltage protection
- **NEVER** exceed rated capacity
- **ALWAYS** verify configuration before activation
- **ALWAYS** have manual override capability

### BLE Communication
- **NEVER** assume communication is reliable or secure
- **NEVER** use over public networks without encryption
- **ALWAYS** validate data integrity
- **ALWAYS** have fallback mechanisms
- **ALWAYS** monitor connection status

### Data Accuracy
- **NEVER** rely solely on software readings for safety decisions
- **NEVER** assume data is correct without validation
- **ALWAYS** use redundant monitoring systems
- **ALWAYS** calibrate and verify readings
- **ALWAYS** have independent safety systems

## NO LIABILITY

THE AUTHORS, CONTRIBUTORS, MAINTAINERS, AND DISTRIBUTORS OF THIS SOFTWARE
SHALL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
OR CONSEQUENTIAL DAMAGES (INCLUDING BUT NOT LIMITED TO: PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; BUSINESS
INTERRUPTION; EQUIPMENT DAMAGE; FIRE; EXPLOSION; PERSONAL INJURY; DEATH; OR
PROPERTY DAMAGE) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING OUT OF OR IN CONNECTION WITH THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## REGULATORY COMPLIANCE

You are solely responsible for:
- Compliance with all local electrical codes
- Compliance with all building codes
- Compliance with fire safety regulations
- Obtaining necessary permits and inspections
- Compliance with utility interconnection requirements
- Compliance with insurance requirements
- FCC/CE compliance for wireless communications
- Environmental regulations for battery disposal

## PROFESSIONAL INSTALLATION STRONGLY RECOMMENDED

This software is intended for advanced users with professional experience in:
- Electrical systems design and installation
- Battery management systems
- Home automation systems
- Modbus and BLE communication protocols
- Safety system design

**If you lack this experience, we STRONGLY recommend:**
- Professional installation by licensed electrician
- Professional configuration by qualified technician
- Regular professional inspection and maintenance
- Professional safety system validation

## MODIFICATIONS AND FORKS

Users who modify, fork, or extend this software:
- Assume ALL risks and liability for their modifications
- Must include this disclaimer in derivative works
- Must clearly identify modifications
- Must not imply endorsement by original authors
- Bear sole responsibility for resulting issues

## EXPERIMENTAL NATURE

This software is:
- Experimental and under active development
- Not certified for safety-critical applications
- Not approved by equipment manufacturers
- Not validated for all hardware configurations
- Subject to breaking changes without notice

## THIRD-PARTY COMPONENTS

This software may depend on third-party libraries and services. The authors
are not responsible for:
- Third-party software bugs or vulnerabilities
- Third-party service availability
- Changes to third-party APIs
- Third-party software licensing issues

## INTELLECTUAL PROPERTY

This software reverse-engineers proprietary protocols. Users are responsible
for ensuring their use complies with:
- Equipment warranty terms
- Manufacturer terms of service
- Local laws regarding reverse engineering
- Intellectual property rights

## DATA AND PRIVACY

Users are responsible for:
- Securing their Home Assistant installation
- Protecting authentication credentials
- Securing BLE communications
- Complying with data privacy regulations
- Backing up configuration data

## ACCEPTANCE OF TERMS

**BY INSTALLING, CONFIGURING, OR USING THIS SOFTWARE, YOU ACKNOWLEDGE THAT:**

1. You have read and understood this entire disclaimer
2. You understand the risks involved
3. You have the necessary technical competence
4. You have appropriate safety measures in place
5. You accept full responsibility for all consequences
6. You agree to hold harmless all authors and contributors
7. You will comply with all applicable laws and regulations
8. You will not use this software in safety-critical applications without appropriate additional safeguards

**IF YOU DO NOT AGREE TO THESE TERMS, DO NOT USE THIS SOFTWARE.**

## QUESTIONS OR CONCERNS

If you have any questions about:
- Safe operation of your equipment
- Proper configuration
- Electrical safety
- Battery safety
- System design

**STOP** and consult with:
- Licensed electrician
- Battery system specialist
- Equipment manufacturer
- Safety professional

## EMERGENCY PROCEDURES

Before using this software, ensure you have:
- Emergency shutdown procedures documented
- Emergency contact numbers readily available
- Fire extinguisher (Class C or ABC) nearby
- First aid kit accessible
- Emergency evacuation plan
- 911 or emergency services contact

## REPORTING ISSUES

If you discover safety issues or bugs:
- Stop using the software immediately
- Report to the project issue tracker
- Do not attempt to fix safety-critical issues yourself
- Share information to help protect other users

---

**Last Updated:** February 5, 2026

**This disclaimer is part of the software license terms and has the same legal effect as the MIT License included with this software.**
