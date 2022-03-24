import config

def main():
    config.init('config.toml')
    cfg = config.config
    cfg.data.put_value('ip', "10.36.56.12")

if __name__ == "__main__":
    main()
