
# Language: en
# Feature: Login


  @smoke @P1
Scenario: Successful login
    # Priority: P1 | Risk Score: 4.25 | Endpoint: POST /api/auth/login
  Given I have a valid user account
  When I POST to /api/auth/login
  Then the response status code should be 200
  And the response should include an access token


  @regression @P2
Scenario: Invalid login credentials
    # Priority: P2 | Risk Score: 3.60 | Endpoint: POST /api/auth/login
  Given I have an invalid user account
  When I POST to /api/auth/login
  Then the response status code should be 401
  And the response should include an error message


  @regression @P2
Scenario: Missing login credentials
    # Priority: P2 | Risk Score: 3.98 | Endpoint: POST /api/auth/login
  Given I have no user account details
  When I POST to /api/auth/login
  Then the response status code should be 400
  And the response should include an error message


  @regression @P2
Scenario: Account lockout after 3 failed login attempts
    # Priority: P2 | Risk Score: 3.78 | Endpoint: POST /api/auth/login
  Given I have a valid user account
  And I have attempted to login 3 times with incorrect credentials
  When I POST to /api/auth/login
  Then the response status code should be 423
  And the response should include an account lockout error message


  @smoke @P2
Scenario: Successful logout
    # Priority: P2 | Risk Score: 3.56 | Endpoint: POST /api/auth/logout
  Given I am logged in
  When I POST to /api/auth/logout
  Then the response status code should be 200
  And the response should not include an access token


  @smoke @P2
Scenario: Successful refresh token
    # Priority: P2 | Risk Score: 3.76 | Endpoint: POST /api/auth/refresh
  Given I am logged in
  And my access token is expired
  When I POST to /api/auth/refresh
  Then the response status code should be 200
  And the response should include a new access token


  @regression @P2
Scenario: Refresh token with invalid refresh token
    # Priority: P2 | Risk Score: 3.60 | Endpoint: POST /api/auth/refresh
  Given I am logged in
  And I have an invalid refresh token
  When I POST to /api/auth/refresh
  Then the response status code should be 401
  And the response should include an error message