create database amulya
use amulya;

CREATE DATABASE amulya;
USE amulya;

drop table login

CREATE TABLE login (
    user_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    access_type ENUM('manager', 'customer') NOT NULL
) AUTO_INCREMENT = 100000;

INSERT INTO login (password, access_type)
VALUES 
    ('password123', 'manager'),
    ('securepass456', 'customer');

DELIMITER $$

CREATE PROCEDURE GetUserAccess(
    IN p_user_id INT,
    IN p_password VARCHAR(255),
    OUT p_status_message VARCHAR(255)
)
BEGIN
    DECLARE p_access_type ENUM('manager', 'customer');

    -- Check if the user_id and password match
    SELECT access_type
    INTO p_access_type
    FROM login
    WHERE user_id = p_user_id AND password = p_password;

    -- Determine the success or failure message
    IF p_access_type IS NOT NULL THEN
        SET p_status_message = CONCAT('Login successful. Access Type: ', p_access_type);
    ELSE
        SET p_status_message = 'Login unsuccessful. Invalid credentials.';
    END IF;
END$$

DELIMITER ;
