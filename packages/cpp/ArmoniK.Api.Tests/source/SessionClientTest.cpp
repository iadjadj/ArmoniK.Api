#include <gtest/gtest.h>

#include "common.h"
#include "logger/formatter.h"
#include "logger/logger.h"
#include "logger/writer.h"

#include "sessions/SessionsClient.h"

using Logger = armonik::api::common::logger::Logger;

TEST(Sessions, can_create_session) {
  Logger log{armonik::api::common::logger::writer_console(), armonik::api::common::logger::formatter_plain(true)};
  std::shared_ptr<::grpc::Channel> channel;
  armonik::api::grpc::v1::TaskOptions task_options;
  init(channel, task_options, log);

  armonik::api::client::SessionsClient client(armonik::api::grpc::v1::sessions::Sessions::NewStub(channel));

  std::string response;
  ASSERT_NO_THROW(response = client.create_session(task_options));
  ASSERT_FALSE(response.empty());

  ASSERT_TRUE(client.get_session(response).status() == armonik::api::grpc::v1::session_status::SESSION_STATUS_RUNNING);
}

TEST(Sessions, can_cancel_session) {
  Logger log{armonik::api::common::logger::writer_console(), armonik::api::common::logger::formatter_plain(true)};
  std::shared_ptr<::grpc::Channel> channel;
  armonik::api::grpc::v1::TaskOptions task_options;
  init(channel, task_options, log);

  armonik::api::client::SessionsClient client(armonik::api::grpc::v1::sessions::Sessions::NewStub(channel));

  std::string session_id = client.create_session(task_options);
  ASSERT_TRUE(client.get_session(session_id).status() ==
              armonik::api::grpc::v1::session_status::SESSION_STATUS_RUNNING);

  armonik::api::grpc::v1::sessions::SessionRaw response;
  ASSERT_NO_THROW(response = client.cancel_session(session_id));
  ASSERT_EQ(response.session_id(), session_id);
  ASSERT_TRUE(client.get_session(session_id).status() ==
              armonik::api::grpc::v1::session_status::SESSION_STATUS_CANCELLED);
}

TEST(Sessions, can_get_session) {
  Logger log{armonik::api::common::logger::writer_console(), armonik::api::common::logger::formatter_plain(true)};
  std::shared_ptr<::grpc::Channel> channel;
  armonik::api::grpc::v1::TaskOptions task_options;
  init(channel, task_options, log);

  armonik::api::client::SessionsClient client(armonik::api::grpc::v1::sessions::Sessions::NewStub(channel));

  std::string session_id = client.create_session(task_options);

  armonik::api::grpc::v1::sessions::SessionRaw response;
  ASSERT_NO_THROW(response = client.get_session(session_id));
  ASSERT_EQ(response.session_id(), session_id);
}

TEST(Sessions, can_list_sessions) {
  Logger log{armonik::api::common::logger::writer_console(), armonik::api::common::logger::formatter_plain(true)};
  std::shared_ptr<::grpc::Channel> channel;
  armonik::api::grpc::v1::TaskOptions task_options;
  init(channel, task_options, log);

  auto client = armonik::api::client::SessionsClient(armonik::api::grpc::v1::sessions::Sessions::NewStub(channel));
  std::string session_ids;
  size_t expected_n_sessions = 5;
  for (size_t i = 0; i < expected_n_sessions; i++) {
    ASSERT_NO_THROW(client.create_session(task_options));
  }

  armonik::api::grpc::v1::sessions::Filters filters;
  int total;
  auto list = client.list_sessions(filters, total);
  ASSERT_GE(list.size(), expected_n_sessions);
  ASSERT_GE(total, expected_n_sessions);
}

TEST(Sessions, can_list_sessions_small_page) {
  Logger log{armonik::api::common::logger::writer_console(), armonik::api::common::logger::formatter_plain(true)};
  std::shared_ptr<::grpc::Channel> channel;
  armonik::api::grpc::v1::TaskOptions task_options;
  init(channel, task_options, log);

  auto client = armonik::api::client::SessionsClient(armonik::api::grpc::v1::sessions::Sessions::NewStub(channel));
  std::string session_ids;
  size_t expected_n_sessions = 5;
  for (size_t i = 0; i < expected_n_sessions; i++) {
    ASSERT_NO_THROW(client.create_session(task_options));
  }

  armonik::api::grpc::v1::sessions::Filters filters;
  int total;
  auto list = client.list_sessions(filters, total, 0, 2);
  ASSERT_EQ(list.size(), 2);
  ASSERT_GE(total, expected_n_sessions);

  list = client.list_sessions(filters, total, -1, 2);
  ASSERT_GE(list.size(), expected_n_sessions);
  ASSERT_GE(total, expected_n_sessions);
}
