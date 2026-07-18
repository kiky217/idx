-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: idx_db
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `bot_events`
--

DROP TABLE IF EXISTS `bot_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bot_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_data` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_run` (`run_id`),
  KEY `idx_type` (`event_type`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `bot_runs`
--

DROP TABLE IF EXISTS `bot_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bot_runs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('BOOTSTRAP','SYNCING','SCANNING','WATCHING','ACTIVE','PAUSED','STOPPED','ERROR') COLLATE utf8mb4_unicode_ci DEFAULT 'BOOTSTRAP',
  `mode` enum('DRY_RUN','LIVE') COLLATE utf8mb4_unicode_ci DEFAULT 'DRY_RUN',
  `started_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` timestamp NULL DEFAULT NULL,
  `error_message` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `run_id` (`run_id`),
  KEY `idx_status` (`status`),
  KEY `idx_started` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `candles`
--

DROP TABLE IF EXISTS `candles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `candles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `timeframe` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '1m/5m/15m',
  `open_time` datetime NOT NULL,
  `open_price` decimal(18,2) NOT NULL,
  `high_price` decimal(18,2) NOT NULL,
  `low_price` decimal(18,2) NOT NULL,
  `close_price` decimal(18,2) NOT NULL,
  `volume` decimal(18,8) DEFAULT '0.00000000',
  `volume_idr` decimal(18,2) DEFAULT '0.00',
  `trade_count` int DEFAULT '0',
  `is_final` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_candle` (`pair_id`,`timeframe`,`open_time`),
  KEY `idx_pair_time` (`pair_id`,`open_time`),
  KEY `idx_final` (`is_final`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `market_summary_current`
--

DROP TABLE IF EXISTS `market_summary_current`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `market_summary_current` (
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_price` decimal(18,2) NOT NULL DEFAULT '0.00',
  `high_24h` decimal(18,2) DEFAULT '0.00',
  `low_24h` decimal(18,2) DEFAULT '0.00',
  `volume_idr` decimal(18,2) DEFAULT '0.00',
  `change_pct` decimal(8,4) DEFAULT '0.0000',
  `spread_pct` decimal(8,4) DEFAULT '0.0000',
  `bid_depth` decimal(18,2) DEFAULT '0.00',
  `ask_depth` decimal(18,2) DEFAULT '0.00',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`pair_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orderbook_metrics`
--

DROP TABLE IF EXISTS `orderbook_metrics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orderbook_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `best_bid` decimal(18,2) DEFAULT '0.00',
  `best_ask` decimal(18,2) DEFAULT '0.00',
  `spread_pct` decimal(8,4) DEFAULT '0.0000',
  `bid_volume_top10` decimal(18,8) DEFAULT '0.00000000',
  `ask_volume_top10` decimal(18,8) DEFAULT '0.00000000',
  `imbalance` decimal(8,4) DEFAULT '0.0000',
  `recorded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_pair_time` (`pair_id`,`recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `client_ref` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `side` enum('BUY','SELL') COLLATE utf8mb4_unicode_ci NOT NULL,
  `order_type` enum('LIMIT','MARKET','STOP_LIMIT') COLLATE utf8mb4_unicode_ci DEFAULT 'LIMIT',
  `price` decimal(18,2) NOT NULL,
  `quantity` decimal(18,8) NOT NULL,
  `amount_idr` decimal(18,2) NOT NULL,
  `status` enum('PENDING','FILLED','PARTIAL','CANCELLED','REJECTED') COLLATE utf8mb4_unicode_ci DEFAULT 'PENDING',
  `filled_quantity` decimal(18,8) DEFAULT '0.00000000',
  `filled_amount_idr` decimal(18,2) DEFAULT '0.00',
  `exchange_order_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `mode` enum('DRY_RUN','LIVE') COLLATE utf8mb4_unicode_ci DEFAULT 'DRY_RUN',
  `signal_id` bigint DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `client_ref` (`client_ref`),
  KEY `idx_pair_status` (`pair_id`,`status`),
  KEY `idx_client_ref` (`client_ref`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pair_rules`
--

DROP TABLE IF EXISTS `pair_rules`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pair_rules` (
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `max_spread_pct` decimal(8,4) DEFAULT '1.0000',
  `min_volume_idr` decimal(18,2) DEFAULT '1000000.00',
  `min_confidence_score` decimal(5,2) DEFAULT '8.00',
  `min_net_risk_reward` decimal(5,2) DEFAULT '2.00',
  `max_position_size_idr` decimal(18,2) DEFAULT '500000.00',
  `cooldown_after_loss_seconds` int DEFAULT '600',
  `is_tradeable` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`pair_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pairs`
--

DROP TABLE IF EXISTS `pairs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pairs` (
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ticker_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `base_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `traded_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volume_precision` int DEFAULT '0',
  `price_precision` int DEFAULT '0',
  `trade_min_base_currency` decimal(18,2) DEFAULT '0.00',
  `trade_min_traded_currency` decimal(18,8) DEFAULT '0.00000000',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`pair_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `positions`
--

DROP TABLE IF EXISTS `positions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `positions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('OPEN','TP1_TAKEN','CLOSED','STOP_LOSS') COLLATE utf8mb4_unicode_ci DEFAULT 'OPEN',
  `entry_price` decimal(18,2) NOT NULL,
  `quantity` decimal(18,8) NOT NULL,
  `amount_idr` decimal(18,2) NOT NULL,
  `stop_loss` decimal(18,2) DEFAULT NULL,
  `tp1_price` decimal(18,2) DEFAULT NULL,
  `tp2_price` decimal(18,2) DEFAULT NULL,
  `tp1_filled_price` decimal(18,2) DEFAULT NULL,
  `tp1_quantity` decimal(18,8) DEFAULT '0.00000000',
  `close_price` decimal(18,2) DEFAULT NULL,
  `close_quantity` decimal(18,8) DEFAULT '0.00000000',
  `pnl_idr` decimal(18,2) DEFAULT '0.00',
  `pnl_pct` decimal(8,4) DEFAULT '0.0000',
  `fee_idr` decimal(18,2) DEFAULT '0.00',
  `buy_order_id` bigint DEFAULT NULL,
  `sell_order_id` bigint DEFAULT NULL,
  `signal_id` bigint DEFAULT NULL,
  `mode` enum('DRY_RUN','LIVE') COLLATE utf8mb4_unicode_ci DEFAULT 'DRY_RUN',
  `opened_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `closed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_pair` (`pair_id`),
  KEY `idx_status` (`status`),
  KEY `idx_opened` (`opened_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `risk_events`
--

DROP TABLE IF EXISTS `risk_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_type` enum('DAILY_LIMIT','COOLDOWN','CIRCUIT_BREAKER','STALE_DATA','SPREAD_TOO_WIDE','CONFIDENCE_LOW','MAX_POSITION','DAILY_LOSS') COLLATE utf8mb4_unicode_ci NOT NULL,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reason` text COLLATE utf8mb4_unicode_ci,
  `blocked_until` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`event_type`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `signals`
--

DROP TABLE IF EXISTS `signals`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `signals` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` enum('BUY','SELL','HOLD','WAIT_AND_SEE') COLLATE utf8mb4_unicode_ci NOT NULL,
  `confidence_score` decimal(5,2) NOT NULL,
  `price` decimal(18,2) NOT NULL,
  `trend_15m` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'bullish/bearish/neutral',
  `momentum_5m` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trigger_1m` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `microstructure_status` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reasons` json DEFAULT NULL,
  `plan_json` json DEFAULT NULL COMMENT 'trade plan if action=BUY',
  `is_executed` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_pair_created` (`pair_id`,`created_at`),
  KEY `idx_action` (`action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trade_minute_stats`
--

DROP TABLE IF EXISTS `trade_minute_stats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade_minute_stats` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `minute_time` datetime NOT NULL,
  `open_price` decimal(18,2) DEFAULT '0.00',
  `close_price` decimal(18,2) DEFAULT '0.00',
  `high_price` decimal(18,2) DEFAULT '0.00',
  `low_price` decimal(18,2) DEFAULT '0.00',
  `volume` decimal(18,8) DEFAULT '0.00000000',
  `volume_idr` decimal(18,2) DEFAULT '0.00',
  `buy_count` int DEFAULT '0',
  `sell_count` int DEFAULT '0',
  `buy_volume` decimal(18,8) DEFAULT '0.00000000',
  `sell_volume` decimal(18,8) DEFAULT '0.00000000',
  `vwap` decimal(18,2) DEFAULT '0.00',
  `largest_trade` decimal(18,2) DEFAULT '0.00',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_minute` (`pair_id`,`minute_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trade_results`
--

DROP TABLE IF EXISTS `trade_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade_results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `position_id` bigint DEFAULT NULL,
  `side` enum('BUY','SELL') COLLATE utf8mb4_unicode_ci NOT NULL,
  `entry_price` decimal(18,2) NOT NULL,
  `exit_price` decimal(18,2) NOT NULL,
  `quantity` decimal(18,8) NOT NULL,
  `amount_idr` decimal(18,2) NOT NULL,
  `gross_pnl_idr` decimal(18,2) DEFAULT '0.00',
  `fee_idr` decimal(18,2) DEFAULT '0.00',
  `net_pnl_idr` decimal(18,2) DEFAULT '0.00',
  `net_pnl_pct` decimal(8,4) DEFAULT '0.0000',
  `holding_seconds` int DEFAULT '0',
  `mode` enum('DRY_RUN','LIVE') COLLATE utf8mb4_unicode_ci DEFAULT 'DRY_RUN',
  `closed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_pair` (`pair_id`),
  KEY `idx_closed` (`closed_at`),
  KEY `idx_mode` (`mode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `watchlist`
--

DROP TABLE IF EXISTS `watchlist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `watchlist` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `pair_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `score` decimal(8,4) DEFAULT '0.0000',
  `volume_rank` int DEFAULT '0',
  `reason` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `active_from` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `active_until` timestamp NULL DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_pair` (`pair_id`),
  KEY `idx_active` (`is_active`,`active_from`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-18 12:24:48
