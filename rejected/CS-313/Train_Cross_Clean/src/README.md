# Railway Level Crossing Control System

A safety-critical control system for managing railway level crossing barriers, implemented in SPARK Ada with formal verification.

## Overview

This system monitors multiple trains and sensor health to ensure road barriers operate safely at railway crossings. It implements the fundamental safety property: **barriers must be down whenever any train is within its danger distance or when sensor faults occur**.

## Safety Philosophy

The system follows the **"Fail-Safe"** principle used in railway engineering:

- **Default state is SAFE** (barriers down)
- **Any uncertainty -> fail to safe state**
- **No single point of failure** (multiple checks)
- **Conservative danger distances** (account for worst-case braking)

## Key Features

### Dynamic Danger Distance Calculation

The system uses a **non-linear danger distance formula** based on physics principles:

```
Danger Distance = 800m + (Speed² / 2)
```

This reflects that kinetic energy (and thus stopping distance) increases with the square of velocity.

**Examples:**
- Train at 0 m/s: 800m danger distance
- Train at 20 m/s: 1,000m danger distance  
- Train at 50 m/s: 2,050m danger distance

### Safety-Critical Monitoring

**Barriers MUST be down if:**
1. Any sensor fault is detected (fail-safe principle)
2. Any present train is within its speed-dependent danger distance

**Barriers may be up only if:**
- All sensors are operational AND
- No trains are in their danger zones

### Multi-Train Tracking

- Monitors up to **3 trains simultaneously**
- Each train tracked with: distance, speed, and presence status
- Independent danger zone calculation for each train

## System Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Monitoring Range** | 10,000m (10 km) | Long-range detection |
| **Base Danger Distance** | 800m | ~65 seconds warning at freight speeds |
| **Maximum Train Speed** | 56 m/s (~200 km/h) | High-speed passenger trains |
| **Number of Trains** | 3 | Typical busy junction capacity |

## Formal Verification

The system uses **SPARK Ada** for formal verification with:

- **Type system** prevents invalid states
- **Loop invariants** prove safety maintained throughout execution
- **Postconditions** prove each operation preserves safety
- **`Is_Safe` function** expresses complete safety property

### Verified Properties

Barriers are always down when any train is in danger zone  
Barriers are always down when sensor faults occur  
Train data always within valid ranges  
No race conditions or state inconsistencies  

## File Structure

```
level_crossing.ads    - Package specification with safety contracts
level_crossing.adb    - Package implementation with safety logic
main.ads              - Main procedure specification
main.adb              - Control loop with invariants
```

## How It Works

### Main Control Loop

The system runs a continuous monitoring loop:

1. **Check sensor health** - Detect any sensor malfunctions
2. **Read train data** - Update position and speed for all trains
3. **Apply safety logic** - Determine correct barrier state
4. **Display status** - Show current system state to operator

### Safety Logic (Monitor_Level_Crossing)

```ada
procedure Monitor_Level_Crossing is
   Must_Close_Barrier : Boolean := False;
begin
   -- Rule 1: Sensor fault -> barriers down
   if Status_System.Sensor_Fault then
      Must_Close_Barrier := True;
   end if;

   -- Rule 2: Any train in danger zone -> barriers down
   for T in Train_ID loop
      if Train_In_Danger_Zone(T) then
         Must_Close_Barrier := True;
      end if;
   end loop;

   -- Apply decision
   Status_System.Barrier_State := 
      (if Must_Close_Barrier then Barrier_Down else Barrier_Up);
end Monitor_Level_Crossing;
```

## Physics Background

### Stopping Distance Formula

For a train traveling at velocity *v* with deceleration *a*:

```
Stopping Distance = v² / (2a)
```

**Example:** Freight train at 56 m/s with 0.5 m/s² deceleration:
- Theoretical stopping distance = 56² / (2 × 0.5) = **3,136m**

The base danger distance (800m) provides additional safety margin for:
- Driver reaction time
- Signal processing delays
- Brake system activation
- Track conditions (wet, icy)

## Usage Example

```
===========================================
Railway Level Crossing Control System v2.0
===========================================
Monitoring 3 trains
Base danger distance: 800m
Danger formula: Base + (Speed^2 / 2)
Max train speed: 56 m/s
===========================================

--- SENSOR STATUS CHECK ---
Are sensors functioning correctly? (1=Yes, 0=No/Fault): 1
Sensors operational.

--- TRAIN 1 DATA ---
Is Train 1 present? (1=Yes, 0=No): 1
Distance from crossing (0-10000 meters): 1500
Train speed (0-56 m/s): 30
  -> Danger distance for this speed: 1250m
  -> Train at safe distance

[... continues for trains 2 and 3 ...]

===========================================
        CURRENT SYSTEM STATUS
===========================================
Sensor Status: Operational

Train 1: PRESENT - Distance: 1500m, Speed: 30m/s (Danger zone: 1250m)
Train 2: Not present
Train 3: Not present

-------------------------------------------
BARRIER STATE: UP
  -> Road is OPEN to traffic
  -> Normal operation
===========================================
```

## Safety Standards Compliance

This system design aligns with principles from:
- **UK Railway Safety Standards** (freight train speeds, braking distances)
- **CENELEC EN 50128** (software for railway control systems)
- **DO-178C** principles (safety-critical software development)

## Building and Running

Requires:
- GNAT Ada compiler with SPARK support
- GNATprove formal verification tool
- AS_IO_Wrapper library for I/O operations

```bash
# Compile with SPARK mode enabled
gnatmake -gnata -gnatwa main.adb

# Run formal verification
gnatprove -P project.gpr --level=2

# Execute
./main
```