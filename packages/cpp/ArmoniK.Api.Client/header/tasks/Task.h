#pragma once

#include "tasks_common.pb.h"
#include <string>
#include <vector>

namespace armonik {
namespace api {
namespace client {
struct TaskCreation {
  std::string payload_id;
  std::vector<std::string> expected_output_keys;
  std::vector<std::string> data_dependencies = {};
  armonik::api::grpc::v1::TaskOptions taskOptions = get_no_task_options();

  static armonik::api::grpc::v1::TaskOptions get_no_task_options() {
    armonik::api::grpc::v1::TaskOptions options;
    options.set_max_retries(INT32_MIN);
    return options;
  }
};

struct TaskInfo {
  /**
   * Id of the task
   */
  std::string task_id;

  /**
   * Expected output result ids
   */
  std::vector<std::string> expected_output_ids;

  /**
   * Data dependencies of the task
   */
  std::vector<std::string> data_dependencies;

  /**
   * Id of the payload
   */
  std::string payload_id;
};
} // namespace client
} // namespace api
} // namespace armonik
