Feature: User Authentication and Role-Based Access Control

  As a user of TestMart
  I want to securely log in and access features based on my role
  So that I can perform my designated tasks within the application

  Background:
    Given the TestMart application is running and accessible

  Scenario: Successful Login for a Customer
    Given a registered "Customer" user exists with email "customer@example.com" and password "SecurePass123"
    When the user logs in with email "customer@example.com" and password "SecurePass123"
    Then the login should be successful
    And an access token and refresh token should be issued
    And the user should be presented with the "Customer Dashboard"

  Scenario: Login Fails with Invalid Credentials
    Given a registered user exists with email "testuser@example.com" and password "ValidPassword123"
    When a user attempts to log in with email "testuser@example.com" and password "IncorrectPassword"
    Then the login should fail
    And an appropriate error message indicating "Invalid email or password" should be displayed
    And no access or refresh tokens should be issued

  Scenario: Account Lockout after Multiple Failed Login Attempts
    Given a registered user exists with email "lockeduser@example.com" and password "CorrectPassword"
    When the user attempts to log in 3 times with email "lockeduser@example.com" and an incorrect password
    Then the account for "lockeduser@example.com" should be locked for 5 minutes
    And a subsequent login attempt for "lockeduser@example.com" should fail
    And an error message "Account locked. Please try again in 5 minutes" should be displayed

  Scenario: Merchant Can Access Product Management Features
    Given a registered "Merchant" user exists with email "merchant@example.com" and password "MerchantPass123"
    When the Merchant successfully logs in with email "merchant@example.com" and password "MerchantPass123"
    Then the "Add new products" button should be visible
    And the Merchant should be able to view "all available products"
    And the "Merchant Dashboard" with store insights should be accessible

  Scenario: Unauthorized Access to Super Admin User Management is Prevented
    Given an unauthenticated user
    When the user attempts to navigate directly to the "Super Admin User Management" page
    Then the user should be redirected to the "Login" page
    And no Super Admin user management content should be displayed