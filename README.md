# Astrobotany

![Astrobotany](https://github.com/michael-lazar/astrobotany/workflows/Astrobotany/badge.svg)

A community garden over the [gemini](https://gemini.circumlunar.space/) protocol. Fork of [jifunks/botany](https://github.com/jifunks/botany).

---

<p align="center">
    🌱&nbsp;•&nbsp;🛰️&nbsp;•&nbsp;🌷&nbsp;•&nbsp;🐝&nbsp;•&nbsp;🚀&nbsp;•&nbsp;🌵&nbsp;•&nbsp;👩‍🚀
    <strong><a href="gemini://astrobotany.mozz.us">gemini://astrobotany.mozz.us</a></strong>
    <a href="https://portal.mozz.us/gemini/astrobotany.mozz.us/">(http&nbsp;proxy)</a>
    🥕&nbsp;•&nbsp;🔭&nbsp;•&nbsp;🌺&nbsp;•&nbsp;👩‍🔬&nbsp;•&nbsp;🌍&nbsp;•&nbsp;👨‍🌾&nbsp;•&nbsp;🌧️
</p>

---


```
Astrobotany

    ---====D     `            _____        +        *     `
     .               '    ,-:` \;',`'-,       |   .
           +    ()      .'-;_,;  ':-;_,'.   - o -        .
 O      `              /;   '/    ,  _`.-\    |   +
                  o   | '`. (`     /` ` \`|           o   *
      '    *   `      |:.  `\`-.   \_   / |                .
   ~*            +    |     (   `,  .`\ ;'|   *        ()
 .         +           \     | .'     `-'/       `
        `        O      `.   ;/        .'   .              O
  +    .              `   `'-._____.-'`         *   '
             *    _(_)_                   `      wWWWw   _
      @@@@       (_)@(_)   vVVVv  .  _     @@@@  (___) _(_)_
     @@()@@ wWWWw  (_)\    (___)   _(_)_  @@()@@   Y  (_)@(_)
 *    @@@@  (___)     `|/    Y    (_)@(_)  @@@@   \|/   (_)\
       /      Y       \|    \|/    /(_)    \|      |/      |
    \ |     \ |/       | / \ | /  \|/       |/    \|      \|/
 jgs\\|//   \\|///  \\\|//\\\|/// \|///  \\\|//  \\|//  \\\|//
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Welcome to astrobotany. You've been given a seed that will grow into a beautiful
plant. Check in and water your plant every 24h to keep it growing. 5 days
without water = death. Your plant depends on you and your friends to live!

“Don't judge each day by the harvest you reap but by the seeds that you plant.”
― Robert Louis Stevenson

[1] 👩‍🌾 Visit your plant
[2] 🌱 Create an account
[3] 📒 Garden directory
[4] 📌 Community message board

Astrobotany is a fork of the original tilde.town pubnix game, Botany.
[5] https://github.com/jifunks/botany

The source code for this gemini capsule can be found here.
[6] https://github.com/michael-lazar/astrobotany
```

## Development Quickstart

### 1. Install

```
git clone git@github.com:michael-lazar/astrobotany.git
cd astrobotany
python3 -m virtualenv venv

source venv/bin/activate
pip install -e .

# Generate a self-signed CA
./scripts/generate_server_ca.sh

# Add a handful of test users
./scripts/add_seed_data.py 10
```

### 2. Run

```
source venv/bin/activate
python main.py
```

### 3. Connect

```
# Generate a signed client certificate
./scripts/generate_client_cert.sh test_user

# Using https://tildegit.org/solderpunk/AV-98
av98 gemini://localhost --tls-cert certs/test_user.cer --tls-key certs/test_user.key
```
