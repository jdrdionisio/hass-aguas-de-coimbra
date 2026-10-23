# Águas de Coimbra - Home Assistant Integration

![Version](https://img.shields.io/github/v/tag/jdrdionisio/hass-aguas-de-coimbra?label=version)

**Disclaimer:** This integration is not affiliated with Águas de Coimbra.

Personal fork of [andre19rodrigues/hass-aguas-de-coimbra](https://github.com/andre19rodrigues/hass-aguas-de-coimbra), kept close to upstream. It adds three things that upstream does not have yet:

- **Subscription picker.** When the account has more than one subscription/site (a second house, a garage), the setup asks which meter to follow instead of silently using the first one in `listSubscriptions`.
- **Meter lookup across subscriptions.** `getContadores` answers HTTP 500 for a subscription without a meter, so the chosen subscription is tried first and, if it has no meter, the remaining ones are tried before giving up.
- **Token renewal.** The portal returns the token expiry in milliseconds; the original comparison in seconds made the token look permanently valid, so every request returned 401 until Home Assistant was restarted. The token is now renewed when it expires, and a rejected token is retried once after a fresh login.

The fork does not run CI. There is no validation badge because there is no automation behind it — run `hassfest` yourself if you need that guarantee.

This Home Assistant integration retrieves telemetry data from your water meter as published on the [Águas de Coimbra website](https://bdigital.aguasdecoimbra.pt/uPortal2/coimbra/index.html).

For precise and real-time water usage, consider installing a dedicated sensor. [Home Assistant](https://www.home-assistant.io/docs/energy/water/) provides several examples.

<img width="339" height="574" alt="sensors" src="https://github.com/user-attachments/assets/2c4d2b2b-ba2a-443f-9f58-2b6bc7034eaf" />


## 💧 Sensors


The integration comprises the following sensors:

| Sensor Name | Unit | Description | Max. update frequency |
|----------------|---------------|------------------|------------|
| `today_consumption` | Litre (L) | Today's water consumption. Sum of all the readings available for the day — typically one per hour, but often inconsistent, with readings occurring only a few times per day. | Every 30 minutes |
| `yesterday_consumption` | Litre (L) | Yesterday's water consumption. Sum of all readings from the previous day. | Once per day |
| `meter_reading` | Cubic meter (m³) | Official meter reading from Águas de Coimbra. Updated once per day around midnight. Although stored as a float, the meter appears to report only the integer part. This is the value that will appear on your invoice. | Once per day |
| `billing_cycle_consumption` | Cubic meter (m³) | Water consumption during the current billing cycle. | Every 30 minutes |
| `billing_cycle_cost` | Euro (€)  | Cost of the billing cycle. | Every 30 minutes |
| `last_successful_refresh` | N/A  | Timestamp of the last API call to Águas de Coimbra. | Every 30 minutes |


**Notes:** 
 - To prevent abuse of the Águas de Coimbra portal, this integration retrieves data only every 30 minutes and limits requests to essential information.
 - `yesterday_consumption` is refetched after a restart and just after midnight, when the portal has not finished publishing the previous day. It can show `0` for a few hours and settle on the real value later in the morning.
 - The billing cycle cost shown is an estimate only. The actual amount on your invoice may differ due to factors such as:
   -  Missing or incomplete data;
   -   Use of an incorrect water meter diameter;
   -   Variations in the billing cycle length (which can range from 28 to 31 days);
   -   Potential inaccuracies in the calculation formula;
   -   Outdated or incorrect pricing information;

This estimate is provided for informational purposes only. Neither this integration nor its contributors accept responsibility for any discrepancies between this estimate and your actual bill.



## 🛠 Installation

### Option 1: HACS (Recommended)

1. Go to **HACS > Integrations**.
2. Click **⋮(three dots) > Custom Repositories**.
3. Add `https://github.com/jdrdionisio/hass-aguas-de-coimbra` and select **Integration** as the category.
4. Click **Add**.
5. Install the integration from HACS.
6. Restart Home Assistant.
7. Go to the **Integrations** page and click **Add Integration**
8. Search for **Águas de Coimbra** and install it.

Requires Home Assistant 2024.11 or newer (declared in `hacs.json`).


### Option 2: Manual

1. Download the contents of this repository.
2. Copy the folder `custom_components/aguas_de_coimbra` to your Home Assistant config folder, at `config/custom_components/aguas_de_coimbra/`.
3. Delete `custom_components/aguas_de_coimbra/__pycache__` if it exists.
4. Restart Home Assistant.
5. Go to the Integrations page and click Add Integration
6. Search for Águas de Coimbra and install it.

Updating an existing installation only means copying the folder again and restarting. Never remove the integration entry from **Devices & Services** to update it: a new entry gets new `unique_id`s and the sensor history is split from the old entities.


## ⚙️ Setup

Enter your credentials for the Águas de Coimbra portal, the billing cycle start day (default is day 1) and whether the social tariff applies. You do not choose the billing day from the portal's own data; set the day your invoice cycle starts.

If the account has more than one subscription, a second step asks which one to follow, showing the supply address, the description and the installation number, with the active subscription first. Accounts with a single subscription skip that step.

![configuration](https://github.com/user-attachments/assets/1d6e536f-4c3b-4cf6-ad64-98f64ff19e0a)

### Changing the subscription later

**Settings > Devices & Services > Águas de Coimbra > Configure**. The same screen has the credentials, the billing day, the social tariff and the subscription dropdown. Saving reloads the integration immediately; no restart is needed.

The dropdown is filled live from the portal, so the portal must be reachable to open that screen. If it is not, the current subscription is kept and the remaining options can still be saved.
