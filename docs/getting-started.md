# Getting started

## Installation

Install `deyecloud` from PyPI:

```bash
pip install deyecloud
```

For development, clone the repository and install in editable mode with the test
dependencies:

```bash
git clone https://github.com/neeythann/deyecloud.git
cd deyecloud
pip install -e ".[test]"
```

## Quickstart

```python
import deyecloud

deye = deyecloud.DeyeCloud(
    app_id="201911067156002",
    app_secret="APPSECRET",
    email="user@example.com",
    password="PASSWORD",
)

for station in deye.station.list():
    print(station.station_name, station.battery_soc)
```

## Configuration

Credentials and other settings can be provided in one of three ways (highest priority
first):

1. Keyword arguments to the `DeyeCloud` constructor
2. Environment variables prefixed with `deye_` (e.g. `deye_app_id`)
3. A `deye.ini` file in the current directory or the user config directory

### Required settings

| Setting        | Description                                              |
|----------------|----------------------------------------------------------|
| `app_id`       | The developer application identifier                     |
| `app_secret`   | The secret paired with `app_id`                          |
| `password`     | The account password (SHA-256 hashed before sending)     |
| one of:        |                                                          |
| `email`        | Login with an email address                              |
| `mobile`       | Login with a mobile number (requires `country_code`)     |
| `username`     | Login with a username                                    |

### Optional settings

| Setting        | Description                                              |
|----------------|----------------------------------------------------------|
| `country_code` | ISO country code, required when using `mobile`           |
| `company_id`   | When set, requests a business-member token. Discover your `companyId` via `deye.account.info()`. Leave unset for a personal-user token |
| `base_url`     | The API base URL (default: `https://eu1-developer.deyecloud.com`) |
| `timeout`      | HTTP timeout in seconds (default: `30`)                  |
| `site_name`    | Select a named section of `deye.ini`                     |

### Example

```python
deye = deyecloud.DeyeCloud(
    app_id="201911067156002",
    app_secret="APPSECRET",
    email="user@example.com",
    password="PASSWORD",
)
```

The same settings in a `deye.ini` file:

```ini
[DEFAULT]
app_id = 201911067156002
app_secret = APPSECRET
email = user@example.com
password = PASSWORD
```

## Authentication

The client obtains a bearer token from `POST /v1.0/account/token` and attaches it as an
`authorization: Bearer ...` header to every subsequent request. Tokens are re-acquired
automatically when they approach expiry, so you generally never need to handle
authentication yourself.

To inspect the current token or account:

```python
token = deye.account.token
account = deye.account.me()
print(account.uid)
```

Business members can list the organizations they belong to:

```python
for org in deye.account.info():
    print(org.company_id, org.company_name)
```
