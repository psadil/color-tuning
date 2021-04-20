
library(hdf5r)
library(tidyverse)
library(patchwork)

f <- H5File$new("data-raw/data.hdf5", mode="r")

data_collection <- f[["data_collection"]]

condition_variables <- data_collection[["condition_variables"]]
d <- condition_variables[["EXP_CV_1"]][] %>% 
  as_tibble() %>%
  mutate(
    task = if_else(shape %in% c("circle", "triangle"), "color", "direction"),
    difficulty = case_when(
      (between(hue, 80, 100) & task == "color")
      | (between(direction, -10, 10) & task == "direction") ~ "hard",
      TRUE ~ "easy"),
    correct = case_when(
      hue == 90 ~ NA,
      direction == 0 ~ NA,
      !is.na(response_time) & str_detect(correct, "True") ~ TRUE,
      TRUE ~ FALSE)) 
  
f$close_all()

N_size <- 3

a <- d %>% 
  filter(!is.na(correct)) %>%
  group_by(block, difficulty) %>%
  summarise(
    N = n(),
    avg = mean(correct),
    s = sum(correct),
    .groups = "drop") %>%
  mutate(
    lower = qbeta(0.025, 1/2 + s, 1/2 + N - s),
    upper = qbeta(0.975, 1/2 + s, 1/2 + N - s)) %>%
  ggplot(aes(x=block)) +
  geom_point(aes(y=avg)) +
  geom_text(aes(label=glue::glue("{N}")), y=1.02, size=N_size) +
  geom_errorbar(aes(ymin=lower, ymax=upper)) +
  facet_wrap(~difficulty, nrow=2, labeller = label_both, strip.position = "right") 


b <- d %>% 
  filter(!is.na(correct)) %>%
  group_by(block, difficulty, task) %>%
  summarise(
    N = n(),
    avg = mean(correct),
    s = sum(correct),
    .groups = "drop") %>%
  mutate(
    lower = qbeta(0.025, 1/2 + s, 1/2 + N - s),
    upper = qbeta(0.975, 1/2 + s, 1/2 + N - s)) %>%
  ggplot(aes(x=block)) +
  geom_point(aes(y=avg)) +
  geom_text(aes(label=glue::glue("{N}")), y=1.03, size=N_size) +
  geom_errorbar(aes(ymin=lower, ymax=upper)) +
  facet_grid(difficulty~task, labeller = label_both) 


a +  b + 
  plot_layout(widths = c(1,2))  +
  theme_gray(base_size = 9) +
  ggsave(
    "accuracy.png",
    width = 7,
    height = 5)
