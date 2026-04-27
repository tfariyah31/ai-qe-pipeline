
# Language: en
# Feature: Login

@smoke
Scenario: Successful login
  Given I have a valid user account
  When I POST to /api/auth/login
  Then the response status code should be 200
  And the response should include an access token

@regression
Scenario: Invalid login credentials
  Given I have an invalid user account
  When I POST to /api/auth/login
  Then the response status code should be 401
  And the response should include an error message

@regression
Scenario: Missing login credentials
  Given I have no user account details
  When I POST to /api/auth/login
  Then the response status code should be 400
  And the response should include an error message

@regression
Scenario: Account lockout after 3 failed login attempts
  Given I have a valid user account
  And I have attempted to login 3 times with incorrect credentials
  When I POST to /api/auth/login
  Then the response status code should be 423
  And the response should include an account lockout error message

@smoke
Scenario: Successful logout
  Given I am logged in
  When I POST to /api/auth/logout
  Then the response status code should be 200
  And the response should not include an access token

@regression
Scenario: Logout without being logged in
  Given I am not logged in
  When I POST to /api/auth/logout
  Then the response status code should be 401
  And the response should include an error message

@regression
Scenario: Refresh token without being logged in
  Given I am not logged in
  When I POST to /api/auth/refresh
  Then the response status code should be 401
  And the response should include an error message

@smoke
Scenario: Successful refresh token
  Given I am logged in
  And my access token is expired
  When I POST to /api/auth/refresh
  Then the response status code should be 200
  And the response should include a new access token

@regression
Scenario: Refresh token with invalid refresh token
  Given I am logged in
  And I have an invalid refresh token
  When I POST to /api/auth/refresh
  Then the response status code should be 401
  And the response should include an error message
