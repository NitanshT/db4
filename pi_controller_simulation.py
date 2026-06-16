"""PI temperature controller — desktop simulation.

Tune Kp and Ki here before deploying to the ESP32.
The thermal model is a first-order system with a peltier cooling term.

Usage:
    python pi_simulation.py
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Tunable gains ────────────────────────────────────────────────────────────
Kp = 0.08       # proportional gain
Ki = 0.002      # integral gain
SETPOINT =17.0 # target temperature (°C)

# ── Thermal model parameters ─────────────────────────────────────────────────
T_AMBIENT   = 25.0   # ambient temperature (°C)
TAU         = 120.0  # thermal time constant (s) — how fast it drifts to ambient
K_PELTIER   = 8.0    # cooling effect per unit PWM (°C/s at full power)
T_INIT      = 25.0   # starting temperature (°C)

# ── Simulation parameters ────────────────────────────────────────────────────
DT          = 1.0    # timestep (s)
DURATION    = 600    # total sim time (s)

# ── PI controller ────────────────────────────────────────────────────────────
def pi_step(error, integral, kp, ki, dt):
    integral += error * dt
    output = kp * error + ki * integral
    output = max(0.0, min(1.0, output))  # clamp PWM 0–1
    return output, integral

# ── Thermal plant model ──────────────────────────────────────────────────────
def plant_step(T, pwm, dt, T_ambient, tau, k_peltier):
    dT = (T_ambient - T) / tau - k_peltier * pwm
    return T + dT * dt

# ── Run simulation ───────────────────────────────────────────────────────────
steps = int(DURATION / DT)
time        = [0.0] * steps
temperature = [0.0] * steps
pwm_log     = [0.0] * steps

T        = T_INIT
integral = 0.0

for i in range(steps):
    error         = SETPOINT - T
    pwm, integral = pi_step(error, integral, Kp, Ki, DT)
    T             = plant_step(T, pwm, DT, T_AMBIENT, TAU, K_PELTIER)

    time[i]        = i * DT
    temperature[i] = T
    pwm_log[i]     = pwm * 100  # store as %

# ── Plot ─────────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

ax1.plot(time, temperature, color='#378ADD', linewidth=1.5, label='temperature')
ax1.axhline(SETPOINT, color='#E24B4A', linewidth=1, linestyle='--', label='setpoint')
ax1.set_ylabel('temperature (°C)')
ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f °C'))
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2.plot(time, pwm_log, color='#1D9E75', linewidth=1.5)
ax2.set_ylabel('PWM output (%)')
ax2.set_xlabel('time (s)')
ax2.set_ylim(0, 105)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pi_simulation.png', dpi=150)
plt.show()