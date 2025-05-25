#include <iostream>
#include <async_await>

async Data fetchData(string url)
{
    Data data = await download(url);
    Data processed = process(data);
    return processed;
}

async bool pushData(Data data, string url)
{
    bool check = await push(url, data);
    return check;
}

int main()
{
    Data processed_data = await async Data(string url) {
        return fetchData(url);
    } ("google.com");
    if (await pushData(processed_data, "my_serv.com"))
        std::cout << "pushed";
    else std::cout << "not pushed";
}
